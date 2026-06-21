# Endpoints de creditos (fiados)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Credit
from pydantic import BaseModel
from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/credits", tags=["Credits"])

# clase CreditCreate
class CreditCreate(BaseModel):
    customer_document: str
    value: Decimal
    order_id: int
    status: str = "A"
    creation_date: date = None

# clase CreditPatch
class CreditPatch(BaseModel):
    status: str

@router.get("/all")
# funcion get all credits
def get_all_credits(db: Session = Depends(get_db)):
    return db.query(Credit).all()

@router.get("/")
# lista los creditos (fiados) con paginacion
def get_credits(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    import math
    q = db.query(Credit)
    total = q.count()
    items = q.order_by(Credit.creation_date.desc()).offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if total > 0 else 1
    return {"items": items, "total": total, "pages": pages}

@router.post("/")
# registra un credito (fiado)
def create_credit(data: CreditCreate, db: Session = Depends(get_db)):
    from datetime import date as dt
    credit = Credit(
        customer_document=data.customer_document,
        value=data.value,
        order_id=data.order_id,
        status=data.status,
        creation_date=data.creation_date or dt.today(),
    )
    db.add(credit)
    db.commit()
    db.refresh(credit)
    return credit

@router.patch("/{id}")
# funcion update credit status
def update_credit_status(id: int, data: CreditPatch, db: Session = Depends(get_db)):
    credit = db.query(Credit).filter(Credit.id == id).first()
    if not credit:
        raise HTTPException(status_code=404, detail="Credito no encontrado")
    credit.status = data.status
    db.commit()
    db.refresh(credit)
    return credit