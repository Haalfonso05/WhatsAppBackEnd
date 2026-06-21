# Endpoints de pedidos y cambio de estado
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.database import get_db, DB_SCHEMA
from app.models import Order, OrderDetail
from app.schemas import OrderCreate, OrderResponse, OrderDetailCreate, OrderDetailResponse
from typing import List

WHATSAPP_TOKEN  = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

# envia un mensaje de texto por la API de WhatsApp
def _send_whatsapp(to: str, message: str):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
    with httpx.Client() as c:
        c.post(url, json=payload, headers=headers)

# clase StatusUpdate
class StatusUpdate(BaseModel):
    status: str 

_STATUS_MAP = {'En espera': 'P', 'Enviado': 'E', 'Listo': 'D', 'Cancelado': 'X'}

router = APIRouter(prefix="/orders", tags=["Orders"])

_DISPLAY_TO_DB = {'En espera': 'P', 'Enviado': 'E', 'Listo': 'D'}

# consulta SQL de pedidos con filtros y paginacion
def _orders_query(db, DB_SCHEMA, search='', status='', page=1, size=20):
    import math
    search_clause = "AND (c.name_1 || ' ' || c.last_name_1 ILIKE :search OR p.name ILIKE :search)" if search else ""
    if status:
        status_clause = """HAVING COALESCE(MAX(d.delivery_status), 'P') != 'X'
        AND CASE
            WHEN COALESCE(MAX(d.delivery_status), 'P') IN ('E', 'D') THEN COALESCE(MAX(d.delivery_status), 'P')
            ELSE 'P'
        END = :db_status"""
    else:
        status_clause = "HAVING COALESCE(MAX(d.delivery_status), 'P') != 'X'"

    params = {'size': size, 'offset': (page - 1) * size}
    if search:
        params['search'] = f'%{search}%'
    if status:
        params['db_status'] = _DISPLAY_TO_DB.get(status, 'P')

    count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT o.id_order
            FROM {DB_SCHEMA}."order" o
            JOIN {DB_SCHEMA}.customer c ON c.document = o.customer_document
            LEFT JOIN {DB_SCHEMA}.order_detail od ON od.order_id = o.id_order
            LEFT JOIN {DB_SCHEMA}.product p ON p.id_product = od.product_id
            LEFT JOIN {DB_SCHEMA}.delivery d ON d.order_id = o.id_order
            WHERE 1=1 {search_clause}
            GROUP BY o.id_order, c.name_1, c.last_name_1, o.total, o.application_date
            {status_clause}
        ) sub
    """
    data_sql = f"""
        SELECT
            o.id_order,
            c.name_1 || ' ' || c.last_name_1 AS client_name,
            COALESCE(STRING_AGG(DISTINCT p.name, ', '), '') AS product_name,
            COALESCE(SUM(od.amount), 0) AS quantity,
            o.total,
            CAST(o.application_date AS TEXT) AS application_date,
            COALESCE(MAX(d.delivery_status), 'P') AS delivery_status,
            COALESCE(MAX(d.observation), '') AS observation
        FROM {DB_SCHEMA}."order" o
        JOIN {DB_SCHEMA}.customer c ON c.document = o.customer_document
        LEFT JOIN {DB_SCHEMA}.order_detail od ON od.order_id = o.id_order
        LEFT JOIN {DB_SCHEMA}.product p ON p.id_product = od.product_id
        LEFT JOIN {DB_SCHEMA}.delivery d ON d.order_id = o.id_order
        WHERE 1=1 {search_clause}
        GROUP BY o.id_order, c.name_1, c.last_name_1, o.total, o.application_date
        {status_clause}
        ORDER BY o.application_date DESC
        LIMIT :size OFFSET :offset
    """

    total = db.execute(text(count_sql), params).scalar()
    rows  = db.execute(text(data_sql), params).mappings().all()
    pages = math.ceil(total / size) if total > 0 else 1
    return {'items': [dict(r) for r in rows], 'total': total, 'pages': pages}

@router.get("/")
# lista los pedidos con paginacion y filtro por estado
def get_orders(page: int = 1, size: int = 20, search: str = "", status: str = "", db: Session = Depends(get_db)):
    return _orders_query(db, DB_SCHEMA, search=search, status=status, page=page, size=size)

@router.get("/{id_order}", response_model=OrderResponse)
# obtiene un pedido por su id
def get_order(id_order: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id_order == id_order).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return order

@router.post("/", response_model=OrderResponse)
# crea un pedido
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    nueva = Order(**order.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.put("/{id_order}", response_model=OrderResponse)
# actualiza un pedido
def update_order(id_order: int, data: OrderCreate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id_order == id_order).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    for key, value in data.model_dump().items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return order

@router.delete("/{id_order}")
# elimina un pedido
def delete_order(id_order: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id_order == id_order).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    db.delete(order)
    db.commit()
    return {"message": "Orden eliminada"}

@router.patch("/{id_order}/status")
# actualiza el estado del pedido y notifica al cliente
def update_order_status(id_order: int, data: StatusUpdate, db: Session = Depends(get_db)):
    db_status = _STATUS_MAP.get(data.status, 'P')

    row = db.execute(text(f"""
        SELECT customer_document FROM {DB_SCHEMA}."order" WHERE id_order = :id
    """), {"id": id_order}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    customer_doc = row[0]

    existing = db.execute(text(f"""
        SELECT id, delivery_status FROM {DB_SCHEMA}.delivery WHERE order_id = :oid LIMIT 1
    """), {"oid": id_order}).fetchone()
    estado_previo = existing[1] if existing else None
    cambio_estado = estado_previo != db_status

    if existing:
        db.execute(text(f"""
            UPDATE {DB_SCHEMA}.delivery
            SET delivery_status = :status
            WHERE order_id = :oid
        """), {"status": db_status, "oid": id_order})
    else:
        db.execute(text(f"""
            INSERT INTO {DB_SCHEMA}.delivery
                (delivery_address, delivery_date, customer_document,
                 hour_start, delivery_status, order_id, value)
            VALUES ('N/A', CURRENT_DATE, :cdoc, NOW(), :status, :oid, 0)
        """), {"cdoc": customer_doc, "status": db_status, "oid": id_order})

    db.commit()

    
    if db_status == 'D' and cambio_estado:
        detalles = db.execute(text(f"""
            SELECT product_id, amount
            FROM {DB_SCHEMA}.order_detail
            WHERE order_id = :oid
        """), {"oid": id_order}).fetchall()

        for detalle in detalles:
            db.execute(text(f"""
                UPDATE {DB_SCHEMA}.product
                SET current_stock = GREATEST(0, current_stock - :amount)
                WHERE id_product = :pid
            """), {"amount": float(detalle[1]), "pid": detalle[0]})

        db.commit()

    if db_status in ('E', 'D') and cambio_estado:
        cliente = db.execute(text(f"""
            SELECT c.phone_number, c.name_1, c.last_name_1
            FROM {DB_SCHEMA}.customer c
            WHERE c.document = :doc
        """), {"doc": customer_doc}).mappings().fetchone()

        if cliente and cliente["phone_number"]:
            detalles_msg = db.execute(text(f"""
                SELECT p.name, od.amount
                FROM {DB_SCHEMA}.order_detail od
                JOIN {DB_SCHEMA}.product p ON p.id_product = od.product_id
                WHERE od.order_id = :oid
            """), {"oid": id_order}).mappings().all()

            nombre = f"{cliente['name_1']} {cliente['last_name_1']}"
            productos = "\n".join([f"- {d['name']} x{int(d['amount'])}" for d in detalles_msg])

            if db_status == 'E':
                msg = f"Hola {nombre}, tu pedido #{id_order} ha sido *enviado*.\n\nProductos:\n{productos}\n\nPronto llegara a tu direccion."
            else:
                msg = f"Hola {nombre}, tu pedido #{id_order} esta *listo* para entrega.\n\nProductos:\n{productos}\n\nGracias por tu compra en Palmita Expres."

            _send_whatsapp(cliente["phone_number"], msg)

    return {"status": data.status}

@router.get("/{id_order}/details")
# obtiene el detalle (productos) de un pedido
def get_order_details(id_order: int, db: Session = Depends(get_db)):
    result = db.execute(text(f"""
        SELECT
            od.product_id,
            p.name AS product_name,
            od.amount,
            ROUND((od.amount * p.reference_price)::numeric, 2) AS subtotal
        FROM {DB_SCHEMA}.order_detail od
        JOIN {DB_SCHEMA}.product p ON p.id_product = od.product_id
        WHERE od.order_id = :order_id
    """), {"order_id": id_order})
    rows = result.mappings().all()
    return [dict(row) for row in rows]

@router.post("/{id_order}/details", response_model=OrderDetailResponse)
# agrega un detalle (producto) a un pedido
def add_order_detail(id_order: int, detail: OrderDetailCreate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id_order == id_order).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    nuevo = OrderDetail(**detail.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo