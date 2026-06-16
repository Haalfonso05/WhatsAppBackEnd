from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import products, orders, customers, credits, webhook

app = FastAPI(title="WhatsApp Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(orders.router)
app.include_router(customers.router)
app.include_router(credits.router)
app.include_router(webhook.router)

@app.get("/")
def root():
    return {"status": "ok"}
