# ADR 002 — Usar DBaaS PostgreSQL da Magalu Cloud

**Status:** Aceito
**Data:** 2026-07-30

## Contexto

A aplicação precisa de persistência de dados. O banco precisa sobreviver a
reinicializações de containers (pods são descartáveis — ver ADR 001) e estar
disponível para múltiplas réplicas da API simultaneamente, sem conflito de conexão.

## Alternativas consideradas

- **DBaaS PostgreSQL gerenciado (externo à VM)** — backup, patch e HA por conta do
  provedor; custo maior; menos controle fino sobre configurações avançadas.
- **PostgreSQL em pod com PVC (dentro do próprio cluster)** — custo baixo, tudo em um
  lugar só; volume, backup e recuperação de desastre ficam por nossa conta; o dado
  morre junto com o cluster se o volume local se perder (mesma VM da ADR 001, sem
  redundância de disco).

## Decisão

Usar o serviço DBaaS PostgreSQL da Magalu Cloud — banco gerenciado, com endereço
**privado** (não exposto à internet), acessado pelos pods via `Secret` do Kubernetes
(`DATABASE_URL`, criado pelo pipeline a partir de um GitHub Secret). Critério:
disponibilidade e custo de operação — estado é caro de operar manualmente, e um banco
em pod dentro da mesma VM efêmera do K3s reintroduziria o mesmo single point of failure
que a ADR 001 já assume para a API.

## Consequências

**Positivas:**
- Backup automático gerenciado pelo provedor
- Sem custo operacional de administração do banco (patch, tuning básico, disco)
- Conexões simultâneas de múltiplas réplicas da API sem conflito
- Rede privada: o banco nunca fica exposto à internet, só alcançável de dentro da VPC
- Sobrevive à recriação da VM do K3s — o dado não está acoplado ao ciclo de vida do
  cluster

**Negativas:**
- Custo por hora de uso, mesmo com pouco tráfego (ao contrário de um pod, não é
  "gratuito" além do preço da VM)
- Menor controle sobre configurações avançadas do PostgreSQL (extensions, tuning fino)
- Dependência do provedor para upgrades de versão
- Acoplamento operacional: se a instância for pausada/desligada (ex.: fim de crédito),
  a aplicação fica com `/health` degradado até religar — comportamento observado e
  documentado na Competência 5 (`docs/evidencias-comp5.md`)

[↑ Voltar à arquitetura](../architecture.md)
