"""Orders backend - minimal FastAPI app for gateway demo."""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Orders Service", version="0.1.0")


class OrderCreate(BaseModel):
    item: str
    quantity: int = 1


ORDERS_DB: list[dict] = [
    {"id": "1", "item": "Widget", "quantity": 2},
    {"id": "2", "item": "Gadget", "quantity": 1},
]


@app.get("/orders")
def list_orders():
    return {"orders": ORDERS_DB}


@app.post("/orders")
def create_order(order: OrderCreate):
    oid = str(len(ORDERS_DB) + 1)
    entry = {"id": oid, "item": order.item, "quantity": order.quantity}
    ORDERS_DB.append(entry)
    return entry


@app.get("/health")
def health():
    return {"status": "ok"}
