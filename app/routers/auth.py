# Endpoints de autenticacion del administrador
import hashlib, secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Employe
from app.schemas import RegisterRequest, LoginRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

# funcion hash
def _hash(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

# funcion hash password
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{salt}:{_hash(password, salt)}"

# funcion verify password
def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split(":", 1)
        return _hash(password, salt) == hashed
    except Exception:
        return False

@router.post("/register", response_model=UserResponse)
# funcion register
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(Employe).filter(Employe.email == data.email.strip().lower()).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    employe = Employe(
        name=data.name.strip(),
        email=data.email.strip().lower(),
        password_hash=hash_password(data.password),
        type="tendero",
    )
    db.add(employe)
    db.commit()
    db.refresh(employe)
    return UserResponse(id=employe.id_card, name=employe.name, email=employe.email)

@router.post("/login", response_model=UserResponse)
# inicia sesion del administrador
def login(data: LoginRequest, db: Session = Depends(get_db)):
    employe = db.query(Employe).filter(Employe.email == data.email.strip().lower()).first()
    if not employe or not employe.password_hash or not verify_password(data.password, employe.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return UserResponse(id=employe.id_card, name=employe.name, email=employe.email)