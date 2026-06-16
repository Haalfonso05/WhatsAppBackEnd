from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.routers import customers, products, orders, credits, auth
from app.database import SessionLocal, DB_SCHEMA

app = FastAPI(
    title="WhatsApp Commerce API",
    description="Backend para sistema de pedidos via WhatsApp",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(credits.router)

from app.routers import webhook
app.include_router(webhook.router)

@app.get("/")
def root():
    return {"message": "WhatsApp Commerce API corriendo"}