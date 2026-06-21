# Conexion y sesion de la base de datos (SQLAlchemy)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DB_SCHEMA = os.getenv("DB_SCHEMA", "whatsapp_commerce")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # verifica la conexión antes de usarla
    pool_recycle=300,        # recicla conexiones cada 5 min (Supabase las cierra antes)
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# clase Base
class Base(DeclarativeBase):
    __table_args__ = {"schema": DB_SCHEMA}

# entrega una sesion de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()