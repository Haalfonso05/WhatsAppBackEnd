from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, ProductType
from app.schemas import ProductCreate, ProductResponse
from pydantic import BaseModel
from typing import List

class StockAdjust(BaseModel):
    delta: float  # positivo suma, negativo resta

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/types")
def get_product_types(db: Session = Depends(get_db)):
    types = db.query(ProductType).all()
    return [{"id": t.id_product_type, "name": t.name} for t in types]

@router.get("/all", response_model=List[ProductResponse])
def get_all_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@router.get("/")
def get_products(page: int = 1, size: int = 25, search: str = "", db: Session = Depends(get_db)):
    import math
    q = db.query(Product)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    pages = math.ceil(total / size) if total > 0 else 1
    return {"items": [ProductResponse.model_validate(i) for i in items], "total": total, "pages": pages}

@router.get("/available", response_model=List[ProductResponse])
def get_available_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.available == "Y").all()

@router.get("/{id_product}", response_model=ProductResponse)
def get_product(id_product: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id_product == id_product).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product

@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    nuevo = Product(**product.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{id_product}", response_model=ProductResponse)
def update_product(id_product: int, data: ProductCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id_product == id_product).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for key, value in data.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product

@router.patch("/{id_product}/stock")
def adjust_stock(id_product: int, data: StockAdjust, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id_product == id_product).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    product.current_stock = max(0, float(product.current_stock) + data.delta)
    db.commit()
    db.refresh(product)
    return {"id_product": product.id_product, "current_stock": float(product.current_stock)}

@router.delete("/{id_product}")
def delete_product(id_product: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id_product == id_product).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(product)
    db.commit()
    return {"message": "Producto eliminado"}
