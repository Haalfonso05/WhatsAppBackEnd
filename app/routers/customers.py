# Endpoints CRUD de clientes
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Customer
from app.schemas import CustomerCreate, CustomerResponse
from typing import List

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get("/all", response_model=List[CustomerResponse])
# funcion get all customers
def get_all_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()

@router.get("/")
# lista los clientes con paginacion y busqueda
def get_customers(page: int = 1, size: int = 25, search: str = "", db: Session = Depends(get_db)):
    import math
    q = db.query(Customer)
    if search:
        q = q.filter(
            Customer.name_1.ilike(f"%{search}%") |
            Customer.last_name_1.ilike(f"%{search}%") |
            Customer.document.ilike(f"%{search}%")
        )
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if total > 0 else 1
    return {"items": [CustomerResponse.model_validate(i) for i in items], "total": total, "pages": pages}

@router.get("/{document}", response_model=CustomerResponse)
# funcion get customer
def get_customer(document: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.document == document).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return customer

@router.post("/", response_model=CustomerResponse)
# crea un cliente
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    existe = db.query(Customer).filter(Customer.document == customer.document).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un cliente con ese documento")
    nuevo = Customer(**customer.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{document}", response_model=CustomerResponse)
# actualiza un cliente
def update_customer(document: str, data: CustomerCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.document == document).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for key, value in data.model_dump().items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer

@router.delete("/{document}")
# funcion delete customer
def delete_customer(document: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.document == document).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.delete(customer)
    db.commit()
    return {"message": "Cliente eliminado"}