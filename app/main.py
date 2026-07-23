import logging
import json
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from scalar_fastapi import get_scalar_api_reference
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db, engine
from app.models import Base, Order, Item

Base.metadata.create_all(bind=engine)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        return json.dumps(log)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Pedidos",
    description="Projeto base do curso Move Tech — Magalu × Prósper Digital Skills",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

Instrumentator().instrument(app).expose(app)


@app.get("/docs", include_in_schema=False)
def docs():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)


class ItemIn(BaseModel):
    sku: str
    description: str
    quantity: int


class OrderIn(BaseModel):
    customer: str


def order_to_dict(order: Order) -> dict:
    return {
        "id": order.id,
        "customer": order.customer,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "items": [
            {"id": i.id, "sku": i.sku, "description": i.description, "quantity": i.quantity}
            for i in order.items
        ],
    }


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unavailable"
    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status}


@app.get("/stats", tags=["health"])
def stats(db: Session = Depends(get_db)):
    total = db.query(Order).count()
    open_orders = db.query(Order).filter(Order.status == "open").count()
    cancelled = db.query(Order).filter(Order.status == "cancelled").count()
    total_items = db.query(Item).count()
    return {
        "orders": {"total": total, "open": open_orders, "cancelled": cancelled},
        "items": {"total": total_items},
    }


@app.post("/orders", status_code=status.HTTP_201_CREATED, tags=["orders"])
def create_order(body: OrderIn, db: Session = Depends(get_db)):
    order = Order(id=str(uuid4()), customer=body.customer)
    db.add(order)
    db.commit()
    db.refresh(order)
    logger.info(json.dumps({"event": "order_created", "order_id": order.id, "customer": order.customer}))
    return order_to_dict(order)


@app.get("/orders", tags=["orders"])
def list_orders(db: Session = Depends(get_db)):
    return [order_to_dict(o) for o in db.query(Order).all()]


@app.get("/orders/{order_id}", tags=["orders"])
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    return order_to_dict(order)


@app.post("/orders/{order_id}/items", status_code=status.HTTP_201_CREATED, tags=["items"])
def add_item(order_id: str, body: ItemIn, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    item = Item(id=str(uuid4()), order_id=order_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "sku": item.sku, "description": item.description, "quantity": item.quantity}


@app.get("/orders/{order_id}/items", tags=["items"])
def list_items(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    return [
        {"id": i.id, "sku": i.sku, "description": i.description, "quantity": i.quantity}
        for i in order.items
    ]


@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["orders"])
def cancel_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    order.status = "cancelled"
    db.commit()
