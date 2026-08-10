# ADR 001 — Usar K3s para deploy da aplicação

**Status:** Aceito
**Data:** 2026-07-28

## Contexto

A aplicação precisa ser implantada na Magalu Cloud de forma acessível publicamente,
resiliente a falhas e com capacidade de escalar. O projeto é um trabalho de estudo
(curso Move Tech), com orçamento e tempo de provisionamento restritos — não é um
sistema com tráfego real ainda.

## Alternativas consideradas

- **K3s em VM** — Kubernetes leve; cobra só a VM; provisionamento < 2 min; sem HA
  nativa (control plane e dados vivem na mesma VM).
- **MKS (Kubernetes Gerenciado)** — control plane e HA gerenciados pela MGC; custo
  maior; provisionamento 5-10 min.
- **VM com Docker Compose** — mais simples de subir; sem orquestração, sem
  self-healing (nada reinicia um container que trava) nem escala declarativa (subir
  réplica é comando manual, não spec versionada).

## Decisão

Usar K3s em uma VM `BV2-2-40` (Ubuntu 24.04) com Klipper ServiceLB para expor a
aplicação na porta 80 do IP público da VM. O script `k3s-mgc` automatiza todo o
provisionamento. Critério: menor custo e provisionamento mais rápido, com manifests
idênticos aos de qualquer cluster Kubernetes — a mesma spec (`k8s/app.yaml`) roda sem
alteração num MKS ou em qualquer outro provedor.

## Consequências

**Positivas:**
- Custo menor que o MKS (cobra apenas pela VM, não pelo control plane)
- Provisionamento em menos de 2 minutos
- Manifests YAML idênticos a qualquer Kubernetes padrão (sem lock-in)
- Restart automático em caso de falha (liveness probe) — comprovado na Competência 5
- Escalabilidade horizontal simples (basta aumentar o número de réplicas)

**Negativas:**
- Single point of failure: sem alta disponibilidade nativa (tudo em uma VM — control
  plane, kubelet e workloads compartilham o mesmo hardware)
- Armazenamento efêmero: volumes locais desaparecem se a VM for recriada
- Sem auto-scaling de nós: capacidade fixa (2 vCPU, 2 GB) — teto real, não
  hipotético: ver a nota de capacidade em `docs/architecture.md`
- IP público muda se a VM for substituída

[↑ Voltar à arquitetura](../architecture.md)
