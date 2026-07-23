# move-tech-cloud-application-comp-3

Ponto de partida da **Competência 3 — Desenvolvimento e Operação de Aplicações (DevOps)**.

Este repositório é um template. Use-o como base para criar o seu próprio repositório e trabalhar na competência.

> Parte do curso **Move Tech** — Magalu × Prósper Digital Skills  
> Formação em Cloud Computing para iniciantes

---

## O que tem aqui

Uma API simples de micro e-commerce com pedidos e itens, construída em Python com FastAPI.

A aplicação armazena os dados em memória. Ainda não tem deploy na nuvem — isso é exatamente o que você vai fazer nesta competência.

### Endpoints disponíveis

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Verifica se a API está no ar |
| `POST` | `/orders` | Cria um novo pedido |
| `GET` | `/orders` | Lista todos os pedidos |
| `GET` | `/orders/{id}` | Retorna um pedido com seus itens |
| `DELETE` | `/orders/{id}` | Cancela um pedido |
| `POST` | `/orders/{id}/items` | Adiciona um item ao pedido |
| `GET` | `/orders/{id}/items` | Lista os itens de um pedido |

---

## O que você vai fazer nesta competência

Ao final da Competência 3, a aplicação deve estar **versionada, conteinerizada e publicada na Magalu Cloud**.

- [ ] Publicar a imagem no Container Registry da Magalu Cloud
- [ ] Criar o manifest Kubernetes (`k8s/app.yaml`)
- [ ] Fazer o deploy no cluster Kubernetes da Magalu Cloud
- [ ] Configurar o pipeline de CI/CD no GitHub Actions

---

## O Dockerfile

O repositório já inclui um `Dockerfile` pronto. Ele define como a aplicação é empacotada em uma imagem Docker:

```dockerfile
FROM python:3.11-slim          # Imagem base com Python 3.11

WORKDIR /app                   # Diretório de trabalho dentro do container

RUN pip install poetry==1.8.3  # Instala o gerenciador de dependências

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-root  # Instala apenas as dependências de produção

COPY app/ ./app/               # Copia o código da aplicação

EXPOSE 8000                    # Porta que a aplicação vai escutar

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

O `docker-compose.yml` usa esse Dockerfile para construir e rodar a aplicação localmente. Na nuvem, o pipeline faz o mesmo — constrói a imagem e publica no registry.

> **Referência:** [Dockerfile — Documentação oficial Docker](https://docs.docker.com/reference/dockerfile/)

---

## Como rodar localmente

**Pré-requisito:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado (Mac e Windows) ou [Docker Engine](https://docs.docker.com/engine/install/) (Linux).

```bash
docker compose up --build
```

Acesse a documentação interativa em: http://localhost:8000/docs

---

## Próxima etapa

Ao concluir esta competência, a solução de referência será publicada em:  
[move-tech-cloud-application-comp-4](https://github.com/move-tech-cloud-computing/move-tech-cloud-application-comp-4)

---

> Inspirado no tutorial [Construindo APIs robustas utilizando Python](https://github.com/luizalabs/tutorial-python-brasil) do LuizaLabs.
