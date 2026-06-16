from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from decimal import Decimal

# Auth
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

# Payment Method
class PaymentMethodBase(BaseModel):
    id_payment_method: int
    name: str

class PaymentMethodResponse(PaymentMethodBase):
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

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    class Config:
        from_attributes = True

# Product Type
class ProductTypeBase(BaseModel):
    id_product_type: int
    name: str

class ProductTypeResponse(ProductTypeBase):
    class Config:
        from_attributes = True

# Product
class ProductCreate(BaseModel):
    name: str
    reference_price: Decimal
    current_stock: Optional[Decimal] = 0
    available: str = "Y"
    product_type_id: int

class ProductResponse(BaseModel):
    id_product: int
    name: str
    reference_price: Decimal
    current_stock: Optional[Decimal] = 0
    available: str
    product_type_id: int
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

class OrderResponse(BaseModel):
    id_order: int
    customer_document: str
    application_date: date
    employe_id_card: Optional[int] = None
    shipment_date: date
    discount: Optional[Decimal] = 0
    total: Decimal
    payment_method_id: int
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

class OrderDetailCreate(OrderDetailBase):
    pass

class OrderDetailResponse(OrderDetailBase):
    line_number: int
    class Config:
        from_attributes = True
