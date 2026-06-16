from sqlalchemy import Column, String, Numeric, Integer, Date, TIMESTAMP, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base, DB_SCHEMA

class PaymentMethod(Base):
    __tablename__ = "payment_method"
    id_payment_method = Column(Integer, primary_key=True, autoincrement=True)
    name              = Column(String(20), nullable=False)

class ProductType(Base):
    __tablename__ = "product_type"
    id_product_type = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(20), nullable=False)

class Customer(Base):
    __tablename__ = "customer"
    document     = Column(String(10), primary_key=True)
    name_1       = Column(String(15), nullable=False)
    name_2       = Column(String(15))
    last_name_1  = Column(String(15), nullable=False)
    last_name_2  = Column(String(15))
    address      = Column(Text)
    phone_number = Column(String(15), nullable=False)

class Product(Base):
    __tablename__ = "product"
    id_product      = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(100), nullable=False)
    reference_price = Column(Numeric(12,2), nullable=False)
    current_stock   = Column(Numeric(10,2), default=0)
    available       = Column(String(1), nullable=False, default="Y")
    product_type_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.product_type.id_product_type"), nullable=False)

class Employe(Base):
    __tablename__ = "employe"
    id_card            = Column(Integer, primary_key=True, autoincrement=True)
    name               = Column(String(90))
    status             = Column(String(1))
    supervisor_id      = Column(Integer, ForeignKey(f"{DB_SCHEMA}.employe.id_card"))
    type               = Column(String(15), nullable=False)
    target_day         = Column(Numeric(10,2))
    functions          = Column(Text)
    daily_rate         = Column(Numeric(12,2))
    number_of_sessions = Column(Integer)
    day_worked         = Column(String(50))
    payment_day        = Column(Numeric(2))
    email              = Column(String(120), unique=True)
    password_hash      = Column(String(128))

class Courier(Base):
    __tablename__ = "courier"
    id_courier = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(90), nullable=False)
    id_card    = Column(String(20), nullable=False)

class Order(Base):
    __tablename__ = "order"
    id_order          = Column(Integer, primary_key=True, autoincrement=True)
    customer_document = Column(String(10), ForeignKey(f"{DB_SCHEMA}.customer.document"), nullable=False)
    application_date  = Column(Date, nullable=False)
    employe_id_card   = Column(Integer, ForeignKey(f"{DB_SCHEMA}.employe.id_card"))
    shipment_date     = Column(Date, nullable=False)
    discount          = Column(Numeric(12,2), default=0)
    total             = Column(Numeric(12,2), nullable=False)
    payment_method_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.payment_method.id_payment_method"), nullable=False)

class OrderDetail(Base):
    __tablename__ = "order_detail"
    line_number       = Column(Integer, primary_key=True, autoincrement=True)
    order_id          = Column(Integer, ForeignKey(f"{DB_SCHEMA}.order.id_order"), nullable=False)
    customer_document = Column(String(10), nullable=False)
    product_id        = Column(Integer, ForeignKey(f"{DB_SCHEMA}.product.id_product"), nullable=False)
    amount            = Column(Numeric(10,2), nullable=False)
    sale_price        = Column(Numeric(12,2), nullable=False)
    subtotal          = Column(Numeric(12,2), nullable=False)

class Delivery(Base):
    __tablename__ = "delivery"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    place             = Column(String(150))
    delivery_address  = Column(String(100), nullable=False)
    delivery_date     = Column(Date, nullable=False)
    customer_document = Column(String(10), nullable=False)
    hour_start        = Column(TIMESTAMP, nullable=False)
    hour_end          = Column(TIMESTAMP)
    observation       = Column(String(500))
    delivery_status   = Column(String(1))
    courier_id        = Column(Integer, ForeignKey(f"{DB_SCHEMA}.courier.id_courier"))
    order_id          = Column(Integer, ForeignKey(f"{DB_SCHEMA}.order.id_order"), nullable=False)
    value             = Column(Numeric(12,2), nullable=False)

class Credit(Base):
    __tablename__ = "credit"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    creation_date     = Column(Date, nullable=False)
    status            = Column(String(1), nullable=False)
    customer_document = Column(String(10), nullable=False)
    payment_date      = Column(Date)
    value             = Column(Numeric(12,2), nullable=False)
    order_id          = Column(Integer, ForeignKey(f"{DB_SCHEMA}.order.id_order"), nullable=False)
