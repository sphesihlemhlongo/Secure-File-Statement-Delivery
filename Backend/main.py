import os
import hmac
import hashlib
import shutil
import time
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

from db import init_db, SessionLocal
from models import User, Document

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
SERVER_SELECTOR_SECRET = os.getenv("SERVER_SELECTOR_SECRET", "dev-selector-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
DOWNLOAD_SECRET = os.getenv("DOWNLOAD_SECRET", "dev-download-secret")
DOWNLOAD_TOKEN_TTL_SECONDS = int(os.getenv("DOWNLOAD_TOKEN_TTL_SECONDS", "900"))

# Security Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utilities
def create_selector(id_number: str) -> str:
    """Deterministic selector for looking up users without exposing ID."""
    return hmac.new(
        SERVER_SELECTOR_SECRET.encode(),
        id_number.encode(),
        hashlib.sha256
    ).hexdigest()

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_selector: str = payload.get("sub")
        if id_selector is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id_selector == id_selector).first()
    if user is None:
        raise credentials_exception
    return user

# Pydantic Models
class RegisterIn(BaseModel):
    name: str
    id_number: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Endpoints
@app.post("/api/register", response_model=Token)
def register(user_in: RegisterIn, db: Session = Depends(get_db)):
    if len(user_in.id_number) != 13 or not user_in.id_number.isdigit():
        raise HTTPException(status_code=400, detail="ID number must be exactly 13 digits")

    id_selector = create_selector(user_in.id_number)
    
    # Check if user exists
    if db.query(User).filter(User.id_selector == id_selector).first():
        raise HTTPException(status_code=400, detail="User already registered")

    id_hash = get_password_hash(user_in.id_number)
    
    new_user = User(
        name=user_in.name,
        id_selector=id_selector,
        id_hash=id_hash
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.id_selector}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # username field contains the 13-digit ID
    id_number = form_data.username
    
    id_selector = create_selector(id_number)
    user = db.query(User).filter(User.id_selector == id_selector).first()
    
    if not user or not verify_password(id_number, user.id_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect ID number",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id_selector}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

class DocumentOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime

    class Config:
        orm_mode = True

@app.post("/api/documents", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file type
    if file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Validate file size (read into memory to check size - for larger files, use chunked reading)
    # Here we read content to check size and write to disk
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Safe filename
    timestamp = int(time.time())
    safe_filename = f"{timestamp}_{current_user.id}_{os.path.basename(file.filename)}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Prevent path traversal (though os.path.basename helps)
    if not os.path.abspath(file_path).startswith(os.path.abspath(UPLOAD_DIR)):
         raise HTTPException(status_code=400, detail="Invalid filename")

    with open(file_path, "wb") as f:
        f.write(content)

    new_doc = Document(
        filename=file.filename,
        filepath=file_path,
        owner_id=current_user.id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    return new_doc

@app.get("/api/documents", response_model=List[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Document).filter(Document.owner_id == current_user.id).all()

# Download Token Logic

def make_download_token(doc_id: int, owner_id: int) -> str:
    """
    Generates a signed token for downloading a document.
    Payload: doc_id|owner_id|expiry_ts
    """
    expiry_ts = int(time.time()) + DOWNLOAD_TOKEN_TTL_SECONDS
    payload = f"{doc_id}|{owner_id}|{expiry_ts}"
    signature = hmac.new(
        DOWNLOAD_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{payload}|{signature}"

def verify_download_token(token: str) -> Optional[dict]:
    """
    Verifies the download token.
    Returns dict with doc_id and owner_id if valid, else None.
    """
    try:
        parts = token.split("|")
        if len(parts) != 4:
            return None
        
        doc_id, owner_id, expiry_ts, signature = parts
        payload = f"{doc_id}|{owner_id}|{expiry_ts}"
        
        expected_signature = hmac.new(
            DOWNLOAD_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_signature, signature):
            return None
            
        if int(time.time()) > int(expiry_ts):
            return None
            
        return {"doc_id": int(doc_id), "owner_id": int(owner_id)}
    except Exception:
        return None

class DownloadTokenOut(BaseModel):
    token: str
    expires_in: int

@app.post("/api/documents/{doc_id}/token", response_model=DownloadTokenOut)
def request_download_token(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    token = make_download_token(doc.id, current_user.id)
    return {"token": token, "expires_in": DOWNLOAD_TOKEN_TTL_SECONDS}

@app.get("/api/download")
def download_document(
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # Security Note: For production scale, consider generating a pre-signed URL 
    # for an object store (like AWS S3) instead of streaming through the application server.
    # Also ensure this endpoint is accessed via HTTPS to protect the token.
    
    data = verify_download_token(token)
    if not data:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
        
    doc = db.query(Document).filter(Document.id == data["doc_id"], Document.owner_id == data["owner_id"]).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not os.path.exists(doc.filepath):
        raise HTTPException(status_code=404, detail="File not found on server")
        
    def iterfile():
        with open(doc.filepath, mode="rb") as file_like:
            yield from file_like

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'}
    )

