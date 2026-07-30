# Micro E-commerce Cloud

![Deploy](https://github.com/monafmenezes/micro-ecommerce-cloud/actions/workflows/deploy.yml/badge.svg)

API REST de pedidos e itens em **FastAPI**, rodando em um cluster **Kubernetes (K3s)** na
**Magalu Cloud**, com deploy automatizado por **GitHub Actions** e persistência em
**PostgreSQL gerenciado (DBaaS)**.

> Projeto desenvolvido durante o curso **Move Tech** — Magalu × Prósper Digital Skills.
> A aplicação base veio do template do curso; a infraestrutura, o pipeline e a
> documentação foram construídos ao longo das competências.

---

## Arquitetura

```
   git push (main)
        │
        ▼
  ┌─────────────────┐   testes → build → push da imagem
  │ GitHub Actions  │   cria o Secret → aplica os manifests
  └─────────────────┘
        │
        ▼
  ┌──────────────────────────────────────────┐
  │  Cluster K3s (VM na Magalu Cloud)        │
  │                                          │
  │   Service (LoadBalancer :80)             │
  │            │                             │
  │            ▼                             │
  │   Deployment — 2 réplicas                │
  │   ┌──────────────┐  ┌──────────────┐     │
  │   │ pod          │  │ pod          │     │
  │   │ FastAPI:8000 │  │ FastAPI:8000 │     │
  │   └──────────────┘  └──────────────┘     │
  │            │  DATABASE_URL (Secret)      │
  └────────────┼─────────────────────────────┘
               │  rede privada
               ▼
      PostgreSQL 17 — DBaaS gerenciado
```

O estado vive **fora** do cluster: os pods são descartáveis e podem ser destruídos sem
perda de dados. A instância do banco só possui endereço privado — não está exposta à internet.

---

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI · Python 3.11 · SQLAlchemy 2.0 |
| Banco | PostgreSQL 17 (DBaaS da Magalu Cloud) |
| Container | Docker · Poetry |
| Orquestração | Kubernetes (K3s) |
| CI/CD | GitHub Actions |
| Observabilidade | health check · liveness/readiness probes · métricas Prometheus |

---

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Estado da API e da conexão com o banco |
| `GET` | `/stats` | Contagem de pedidos e itens |
| `POST` | `/orders` | Cria um pedido |
| `GET` | `/orders` | Lista todos os pedidos |
| `GET` | `/orders/{id}` | Retorna um pedido com seus itens |
| `DELETE` | `/orders/{id}` | Cancela um pedido (*soft delete*) |
| `POST` | `/orders/{id}/items` | Adiciona um item ao pedido |
| `GET` | `/orders/{id}/items` | Lista os itens de um pedido |
| `GET` | `/docs` | Documentação interativa (Scalar) |
| `GET` | `/metrics` | Métricas no formato Prometheus |

---

## As competências

Este repositório atravessa duas competências do curso. A aplicação (FastAPI) já vinha
pronta no template — o trabalho foi de infraestrutura, pipeline e persistência.

### Competência 3 — DevOps e Deploy ✅

Versionar, conteinerizar e publicar a aplicação na Magalu Cloud.

- [x] Publicar a imagem no Container Registry da Magalu Cloud
- [x] Criar o manifest Kubernetes (`k8s/app.yaml`)
- [x] Fazer o deploy no cluster Kubernetes da Magalu Cloud
- [x] Configurar o pipeline de CI/CD no GitHub Actions

**Decisões que valem registro:**
- O `Deployment` sobe **2 réplicas** com `readinessProbe` e `livenessProbe` apontando para
  `/health` — readiness protege o usuário durante o boot, liveness reinicia pod travado.
- A imagem é publicada com o **SHA do commit** além de `latest`, e o manifesto recebe a tag
  via `envsubst`. Com tag fixa, o `kubectl apply` responde `unchanged` e **nenhum rollout
  acontece** — o pipeline ficaria verde sem deployar nada.
- O pipeline termina com `kubectl rollout status --timeout=180s`, para reportar deploy
  **concluído**, não deploy **pedido**.

### Competência 4 — Gestão de Dados e Persistência ✅

Conectar a aplicação a um PostgreSQL gerenciado, com os dados sobrevivendo a redeploys.

- [x] Documentar a modelagem de dados (`docs/data-model.md`)
- [x] Provisionar a instância PostgreSQL no DBaaS da Magalu Cloud
- [x] Adicionar a `DATABASE_URL` ao `k8s/app.yaml`, lida de um Kubernetes Secret
- [x] Criar o Secret pelo pipeline, a cada deploy

**Decisões que valem registro:**
- O valor do secret é passado ao `kubectl` por **variável de ambiente**, não interpolado
  direto no `run:` — senha de banco tem caractere especial, e `${{ }}` é substituído como
  texto puro antes de o shell existir.
- A instância só tem **endereço privado**: os pods alcançam, a internet não.
- A persistência foi validada **destruindo os pods** (`kubectl delete pods --all`), não
  apenas redeployando — ver [evidências](docs/evidencias.md).

---

## O Dockerfile

A aplicação é empacotada em uma imagem Docker:

```dockerfile
FROM python:3.11-slim          # Imagem base com Python 3.11

WORKDIR /app                   # Diretório de trabalho dentro do container

RUN pip install poetry==1.8.3  # Instala o gerenciador de dependências

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-root  # Apenas dependências de produção

COPY app/ ./app/               # Copia o código da aplicação

EXPOSE 8000                    # Porta que a aplicação vai escutar

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

O `docker-compose.yml` usa esse Dockerfile para rodar a aplicação localmente. Na nuvem, o
pipeline faz o mesmo — constrói a imagem e publica no registry.

> **Referência:** [Dockerfile — Documentação oficial Docker](https://docs.docker.com/reference/dockerfile/)

---

## Rodando localmente

**Pré-requisito:** Docker.

```bash
docker compose up --build
```

Documentação interativa em http://localhost:8000/docs

Sem a variável `DATABASE_URL`, a aplicação usa SQLite local — os dados não sobrevivem ao
reinício do container. Para apontar para um PostgreSQL:

```bash
export DATABASE_URL="postgresql://usuario:senha@host:5432/orders"
```

> ⚠️ Caracteres especiais na senha precisam de *percent-encoding* na URL
> (`@` → `%40`), já que a string de conexão é uma URL.

---

## Deploy

O pipeline roda a cada push na `main` (ou pelo botão *Run workflow*) e executa:

1. `pytest`
2. build da imagem e push para o Container Registry da Magalu Cloud
3. criação do `Secret` do banco no cluster
4. `kubectl apply` dos manifests e espera do rollout

A imagem é publicada com **duas tags**: o SHA do commit e `latest`. O manifesto usa o SHA —
com uma tag fixa, o `kubectl apply` responderia `unchanged` e nenhum rollout aconteceria.

### Configuração necessária

Secrets do repositório (*Settings → Secrets and variables → Actions*):

| Secret | Conteúdo |
|---|---|
| `MGC_REGISTRY_USER` | usuário do Container Registry |
| `MGC_REGISTRY_PASSWORD` | senha do Container Registry |
| `MGC_REGISTRY_NAME` | nome do registry na Magalu Cloud |
| `MGC_KUBECONFIG` | conteúdo do `kubeconfig.yaml` do cluster |
| `DATABASE_URL` | string de conexão do PostgreSQL |

Nenhuma credencial fica no código ou nos manifests: a `DATABASE_URL` sai do cofre do
GitHub, vira um `Secret` do Kubernetes e chega ao container como variável de ambiente.

---

## Estrutura

```
.
├── app/
│   ├── main.py          # rotas, health check e métricas
│   ├── models.py        # modelos SQLAlchemy (Order, Item)
│   └── database.py      # engine e sessão — lê DATABASE_URL
├── k8s/
│   └── app.yaml         # Deployment (2 réplicas, probes) + Service
├── .github/workflows/
│   └── deploy.yml       # pipeline de CI/CD
├── docs/
│   ├── data-model.md    # modelagem de dados
│   └── evidencias.md    # evidências de execução
└── tests/
```

---

## Documentação

- [**Modelagem de dados**](docs/data-model.md) — entidades, relacionamento 1:N e onde cada
  regra é garantida (banco ou aplicação)
- [**Evidências de execução**](docs/evidencias.md) — saídas reais do cluster, incluindo o
  teste de persistência

---

> Aplicação base inspirada no tutorial
> [Construindo APIs robustas utilizando Python](https://github.com/luizalabs/tutorial-python-brasil)
> do LuizaLabs.
