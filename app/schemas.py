# Esquemas Pydantic para validar entradas y salidas
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from decimal import Decimal

# Auth
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

# clase LoginRequest
class LoginRequest(BaseModel):
    email: str
    password: str

# clase UserResponse
class UserResponse(BaseModel):
    id: int
    name: str
    email: str

# Payment Method
class PaymentMethodBase(BaseModel):
    id_payment_method: int
    name: str

# clase PaymentMethodResponse
class PaymentMethodResponse(PaymentMethodBase):
    # clase Config
    class Config:
        from_attributes = True

# Customer
class CustomerBase(BaseModel):
    document: str
    name_1: str
    name_2: Optional[str] = None
    last_name_1: str
    last_name_2: Optional[str] = None
    address: Optional[str] = None
    phone_number: str

# clase CustomerCreate
class CustomerCreate(CustomerBase):
    pass

# clase CustomerResponse
class CustomerResponse(CustomerBase):
    # clase Config
    class Config:
        from_attributes = True

# Product Type
class ProductTypeBase(BaseModel):
    id_product_type: int
    name: str

# clase ProductTypeResponse
class ProductTypeResponse(ProductTypeBase):
    # clase Config
    class Config:
        from_attributes = True

# Product
class ProductCreate(BaseModel):
    name: str
    reference_price: Decimal
    current_stock: Optional[Decimal] = 0
    available: str = "Y"
    product_type_id: int

# clase ProductResponse
class ProductResponse(BaseModel):
    id_product: int
    name: str
    reference_price: Decimal
    current_stock: Optional[Decimal] = 0
    available: str
    product_type_id: int
    # clase Config
    class Config:
        from_attributes = True

# Order
class OrderCreate(BaseModel):
    customer_document: str
    application_date: date
    employe_id_card: Optional[int] = None
    shipment_date: date
    discount: Optional[Decimal] = 0
    total: Decimal
    payment_method_id: int

# clase OrderResponse
class OrderResponse(BaseModel):
    id_order: int
    customer_document: str
    application_date: date
    employe_id_card: Optional[int] = None
    shipment_date: date
    discount: Optional[Decimal] = 0
    total: Decimal
    payment_method_id: int
    # clase Config
    class Config:
        from_attributes = True

# Order Detail
class OrderDetailBase(BaseModel):
    order_id: int
    customer_document: str
    product_id: int
    amount: Decimal
    sale_price: Decimal
    subtotal: Decimal

# clase OrderDetailCreate
class OrderDetailCreate(OrderDetailBase):
    pass

# clase OrderDetailResponse
class OrderDetailResponse(OrderDetailBase):
    line_number: int
    # clase Config
    class Config:
        from_attributes = True