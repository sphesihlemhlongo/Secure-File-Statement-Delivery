import os
import hmac
import hashlib
import time
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt, JWTError
from google import genai

from db import supabase
from models import User, Document
from config import settings
from schemas import RegisterIn, Token, DocumentOut, DownloadTokenOut, ChatRequest


# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Security Setup
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup and shutdown events.
    """
    logger.info("Application startup: Initializing resources...")
    
    # Logging configuration status (without secrets)
    logger.info(f"Upload Directory: {settings.upload_dir}")
    
    try:
        # Supabase Health Check
        logger.info("Verifying Supabase connection...")
        
        # Tables are created via SQL Supabase dashboard.
        response = supabase.table("users").select("id").limit(1).execute()
        logger.info("Supabase connection verified.")
    except Exception as e:
        logger.critical(f"CRITICAL: Supabase connection failed. Error: {e}")
        raise

    # Ensuring upload directory exists
    if not os.path.exists(settings.upload_dir):
        try:
            os.makedirs(settings.upload_dir)
            logger.info(f"Created upload directory at {settings.upload_dir}")
        except OSError as e:
            logger.error(f"Failed to create upload directory {settings.upload_dir}: {e}")

    logger.info("Application startup complete.")
    yield
    logger.info("Application shutdown: Cleaning up resources...")

app = FastAPI(
    title="Secure Statement Delivery",
    lifespan=lifespan,
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities
def create_selector(id_number: str) -> str:
    """Deterministic selector for looking up users without exposing ID."""
    return hmac.new(
        settings.server_selector_secret.encode(),
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
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        id_selector: Optional[str] = payload.get("sub")
        if id_selector is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    try:
        response = supabase.table("users").select("*").eq("id_selector", id_selector).limit(1).execute()
        if not response.data:
            raise credentials_exception
        # Convert dict to Pydantic model
        user_data = response.data[0]
        return User(**user_data)
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise credentials_exception

# Endpoints
@app.post("/api/register", response_model=Token)
def register(user_in: RegisterIn):
    # ID validation is handled by Pydantic V2 model in schemas.py
    
    id_selector = create_selector(user_in.id_number)
    
    # Checking if user exists
    try:
        existing_user = supabase.table("users").select("id").eq("id_selector", id_selector).execute()
        if existing_user.data:
            raise HTTPException(status_code=400, detail="User already registered")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Database error during registration check: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    id_hash = get_password_hash(user_in.id_number)
    
    new_user_data = {
        "name": user_in.name,
        "id_selector": id_selector,
        "id_hash": id_hash,
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        response = supabase.table("users").insert(new_user_data).execute()
        if not response.data:
             raise HTTPException(status_code=500, detail="Failed to create user")
        
        # Supabase returns the created object
        created_user = response.data[0]
        
    except Exception as e:
        logger.error(f"Database error during registration insert: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # Ensuring created_user is a dict before accessing
    if not isinstance(created_user, dict):
         logger.error(f"Unexpected response format from Supabase: {created_user}")
         raise HTTPException(status_code=500, detail="Internal Server Error")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(created_user.get('id_selector'))}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # username field contains the 13-digit ID
    id_number = form_data.username
    
    id_selector = create_selector(id_number)
    
    try:
        response = supabase.table("users").select("*").eq("id_selector", id_selector).limit(1).execute()
        user_data = response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Database error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    if not user_data or not isinstance(user_data, dict) or not verify_password(id_number, str(user_data.get('id_hash'))):
        logger.warning(f"Failed login attempt for selector {id_selector}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect ID number",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user_data.get('id_selector'))}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/documents", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Validating file type
    if not file.filename or file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Validating file size (reading into memory to check size - for larger files, using chunked reading)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Safe filename
    timestamp = int(time.time())
    safe_filename = f"{timestamp}_{current_user.id}_{os.path.basename(file.filename)}"
    
    # Using system temp directory for Vercel compatibility
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, safe_filename)

    try:
        # 1. Saving to temp folder
        with open(temp_file_path, "wb") as f:
            f.write(content)
            
        # 2. Uploading to Supabase Storage
        # I used the 'documents' bucket in Supabase.
        storage_path = f"{current_user.id}/{safe_filename}"
        with open(temp_file_path, "rb") as f:
            supabase.storage.from_("documents").upload(
                path=storage_path,
                file=f,
                file_options={"content-type": "application/pdf"}
            )
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail="Could not save file")
    finally:
        # Cleaning up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    new_doc_data = {
        "filename": file.filename,
        "filepath": storage_path, # Storing storage path instead of local path
        "owner_id": current_user.id,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    try:
        response = supabase.table("documents").insert(new_doc_data).execute()
        if not response.data:
             raise HTTPException(status_code=500, detail="Failed to save document metadata")
        created_doc = response.data[0]
    except Exception as e:
        logger.error(f"Database error during document upload: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    if not isinstance(created_doc, dict):
         logger.error(f"Unexpected response format from Supabase: {created_doc}")
         raise HTTPException(status_code=500, detail="Internal Server Error")

    logger.info(f"User {current_user.id} uploaded document {created_doc.get('id')}")
    return Document(**created_doc)

@app.get("/api/documents", response_model=List[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user)
):
    try:
        response = supabase.table("documents").select("*").eq("owner_id", current_user.id).execute()
        return [Document(**doc) for doc in response.data]
    except Exception as e:
        logger.error(f"Database error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Downloading Token Logic

def make_download_token(doc_id: int, owner_id: int) -> str:
    """
    Generates a signed token for downloading a document.
    Payload: doc_id|owner_id|expiry_ts
    """
    expiry_ts = int(time.time()) + settings.download_token_ttl_seconds
    payload = f"{doc_id}|{owner_id}|{expiry_ts}"
    signature = hmac.new(
        settings.download_secret.encode(),
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
            settings.download_secret.encode(),
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

@app.post("/api/documents/{doc_id}/token", response_model=DownloadTokenOut)
def request_download_token(
    doc_id: int,
    current_user: User = Depends(get_current_user)
):
    try:
        response = supabase.table("documents").select("*").eq("id", doc_id).eq("owner_id", current_user.id).limit(1).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        doc_data = response.data[0]
        if not isinstance(doc_data, dict):
             raise ValueError("Invalid data format")
        doc = Document(**doc_data)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Database error requesting token: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
        
    token = make_download_token(doc.id, current_user.id)
    return {"token": token, "expires_in": settings.download_token_ttl_seconds}

@app.get("/api/download")
def download_document(
    token: str = Query(...)
):
    data = verify_download_token(token)
    if not data:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
        
    try:
        response = supabase.table("documents").select("*").eq("id", data["doc_id"]).eq("owner_id", data["owner_id"]).limit(1).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        doc = Document(**response.data[0])
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Database error during download: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
        
    # Downloading from Supabase Storage to temp file
    try:
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"download_{doc.id}_{int(time.time())}.pdf")
        
        file_bytes = supabase.storage.from_("documents").download(doc.filepath)
        
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)
            
    except Exception as e:
        logger.error(f"Storage download error: {e}")
        raise HTTPException(status_code=404, detail="File not found on server")
        
    def iterfile():
        try:
            with open(temp_file_path, mode="rb") as file_like:
                yield from file_like
        finally:
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.error(f"Failed to cleanup temp file {temp_file_path}: {e}")

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'}
    )

async def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    """
    Returns the current user if authenticated, else None.
    Does not raise HTTPException for missing/invalid credentials.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        id_selector: Optional[str] = payload.get("sub")
        if id_selector is None:
            return None
    except JWTError:
        return None
    
    try:
        response = supabase.table("users").select("*").eq("id_selector", id_selector).limit(1).execute()
        if not response.data:
            return None
        user_data = response.data[0]
        return User(**user_data)
    except Exception:
        return None

# AI Chatbot
# I used the settings.gemini_api_key which maps to the 'Gemini' env var.
client = genai.Client(api_key=settings.gemini_api_key)

@app.post("/api/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    try:
        user_context = ""
        if current_user:
            user_context = f"The user's name is {current_user.name}. Address them by name occasionally."

        system_prompt = (
            "You are a helpful and friendly financial security assistant for Capitec's Secure File Statement Delivery system. "
            "Your goal is to help users with financial security questions and how to use this system. "
            "The system allows users to upload PDF statements, view them, and generate secure, time-limited download links (valid for 3 minutes). "
            "Keep your answers short, concise, and friendly. "
            f"{user_context} "
            "Do not provide financial advice, only security best practices and system usage help. "
            "If asked about things unrelated to financial security or this system, politely decline."
        )
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{system_prompt}\n\nUser: {request.message}"
        )
        return {"response": response.text}
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail="AI service unavailable")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

