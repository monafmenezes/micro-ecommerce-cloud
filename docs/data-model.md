# Modelagem de Dados

Modelagem da API de pedidos, definida em [`app/models.py`](../app/models.py) via SQLAlchemy ORM.

Até a Competência 3 essas tabelas viviam num SQLite **dentro do pod** — sumiam a cada
reinício. Na Competência 4 elas passam a morar num PostgreSQL gerenciado no DBaaS da
Magalu Cloud, fora do cluster. O código da aplicação não muda: `app/database.py` lê a
variável de ambiente `DATABASE_URL` e o SQLAlchemy fala com o banco que ela apontar.

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orders.db")
```

---

## Entidades

### Pedido (`orders`)

| Coluna | Tipo Python | Tipo no PostgreSQL | Nulo? | Descrição |
|---|---|---|---|---|
| `id` | `str` | `VARCHAR` **PK** | não | UUID4 em texto. Gerado **pela aplicação**, não pelo banco. |
| `customer` | `str` | `VARCHAR` | **não** | Nome do cliente. Único campo realmente obrigatório na criação. |
| `status` | `str` | `VARCHAR` | sim ⚠️ | `"open"` ou `"cancelled"`. O default `"open"` é aplicado **pela aplicação**. |
| `created_at` | `datetime` | `TIMESTAMP WITH TIME ZONE` | sim ⚠️ | Instante da criação, em UTC. Preenchido **pela aplicação**. |

### Item (`items`)

| Coluna | Tipo Python | Tipo no PostgreSQL | Nulo? | Descrição |
|---|---|---|---|---|
| `id` | `str` | `VARCHAR` **PK** | não | UUID4 em texto. Gerado pela aplicação. |
| `order_id` | `str` | `VARCHAR` **FK → `orders.id`** | **não** | Pedido a que o item pertence. |
| `sku` | `str` | `VARCHAR` | **não** | Código do produto. |
| `description` | `str` | `VARCHAR` | **não** | Descrição livre do item. |
| `quantity` | `int` | `INTEGER` | **não** | Quantidade pedida. Sem restrição de valor mínimo no banco. |

> Os campos `String` são declarados **sem tamanho máximo**. No PostgreSQL isso vira um
> `VARCHAR` sem limite — que se comporta como `TEXT`, sem penalidade de performance.
> Consequência prática: **não há validação de comprimento em lugar nenhum**, nem no banco
> nem nos modelos Pydantic de entrada (`app/main.py`).

---

## Relacionamento

Um pedido tem muitos itens; cada item pertence a exatamente um pedido — **1:N**.

```
┌─────────────────────┐          ┌──────────────────────┐
│       orders        │          │        items         │
├─────────────────────┤          ├──────────────────────┤
│ id          (PK)    │─────┐    │ id           (PK)    │
│ customer            │  1  └──N─│ order_id     (FK)    │
│ status              │          │ sku                  │
│ created_at          │          │ description          │
└─────────────────────┘          │ quantity             │
                                 └──────────────────────┘
```

No ORM o vínculo é declarado nos dois sentidos, com `back_populates`:

```python
# Order
items: Mapped[list["Item"]] = relationship(
    "Item", back_populates="order", cascade="all, delete-orphan"
)

# Item
order: Mapped["Order"] = relationship("Order", back_populates="items")
```

---

## Onde cada regra é garantida — banco ou aplicação?

Esta é a seção mais importante do documento. Boa parte do que *parece* ser regra do banco
está, na verdade, escrita em Python — e só vale para quem entra pela API.

| Regra | Escrita em | O banco sabe? |
|---|---|---|
| `id` = UUID4 | Python (`default=lambda: str(uuid4())`) | ❌ não há `DEFAULT` no schema |
| `status` = `"open"` | Python | ❌ |
| `created_at` = agora (UTC) | Python | ❌ |
| `customer` obrigatório | ambos (`nullable=False`) | ✅ `NOT NULL` |
| item aponta para pedido existente | ambos (`ForeignKey`) | ✅ constraint de FK |
| apagar pedido apaga os itens | **Python** (`cascade="all, delete-orphan"`) | ❌ a FK **não** tem `ON DELETE CASCADE` |

### O que isso significa na prática

**Inserção fora da aplicação.** Um `INSERT` feito direto no `psql` (ou por um script de
carga) não recebe nenhum dos defaults. `status` e `created_at` ficam `NULL`. Como o
endpoint `/stats` conta pedidos filtrando por `status == "open"` e `status == "cancelled"`,
uma linha com `status` nulo **não aparece em nenhuma das contagens** — desaparece do
relatório sem gerar erro algum.

**Exclusão fora da aplicação.** Um `DELETE FROM orders` no `psql` deixa os itens órfãos:
o cascade é executado pelo SQLAlchemy, que carrega os filhos em memória e emite os
`DELETE` um a um. O PostgreSQL não recebeu instrução nenhuma a respeito.

**Nota:** hoje a aplicação **nunca apaga um pedido**. O endpoint `DELETE /orders/{id}`
(`app/main.py`) faz *soft delete* — apenas grava `status = "cancelled"`. O cascade
declarado no modelo protege, portanto, um caminho que a aplicação não percorre.

**Sem índice na FK.** O PostgreSQL **não** cria índice automaticamente para chaves
estrangeiras. As consultas de `GET /orders/{id}/items` filtram por `items.order_id` sem
índice — irrelevante no volume deste projeto, relevante em produção.

---

## Como as tabelas são criadas

Na subida da aplicação, `app/main.py` executa:

```python
Base.metadata.create_all(bind=engine)
```

O `create_all()` verifica quais tabelas do modelo **ainda não existem** no banco e emite
`CREATE TABLE` apenas para essas. É o que faz o primeiro deploy contra o Postgres novo
funcionar sem nenhum passo manual de schema.

⚠️ **O que ele não faz:** se a tabela já existe, o `create_all()` **não a compara com o
modelo e não a altera** — e não emite aviso nenhum. Adicionar uma coluna nova em
`app/models.py` e fazer deploy produz:

- `create_all()` executa **sem erro**
- o pod fica `Running`, os probes passam, o pipeline fica **verde**
- a aplicação quebra no primeiro request que tocar a coluna nova, com erro vindo **do
  banco**, em tempo de execução

Ou seja: **um deploy bem-sucedido informando que está tudo certo, com o schema errado.**

É por isso que o [Alembic](https://alembic.sqlalchemy.org/) consta em `pyproject.toml` sem
estar em uso: ele é a ferramenta de *migrations*, que versiona as mudanças de schema e
aplica `ALTER TABLE` com histórico. Nesta competência ele fica de reserva — `create_all()`
basta porque o schema não muda.

### ⚠️ O banco `orders` não é criado automaticamente

O `create_all()` cria **tabelas**, nunca um **banco**. A instância provisionada no DBaaS
não vem com o banco `orders` — ele precisa ser criado manualmente no painel antes do
primeiro deploy. Sem ele, a `DATABASE_URL` aponta para um destino inexistente e a conexão
falha na subida do pod.

---

## Migração de SQLite para PostgreSQL

Nenhum dado é migrado: o SQLite da Competência 3 vivia dentro do container e seu conteúdo
era efêmero por definição. O Postgres começa vazio, e as tabelas nascem no primeiro deploy.

A única diferença de tipo com efeito real é `created_at`. O SQLite não possui tipo de
data — armazena o valor como texto, e o SQLAlchemy o converte na leitura. O PostgreSQL
usa `TIMESTAMPTZ` nativo, com fuso de verdade e comparação temporal correta. Como a
aplicação sempre grava `datetime.now(timezone.utc)`, o comportamento visível permanece o
mesmo; o que muda é o banco passar a tratar o campo como um instante no tempo, e não como
uma string.
