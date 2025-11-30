from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class RegisterIn(BaseModel):
    name: str
    id_number: str = Field(..., min_length=13, max_length=13, pattern=r"^\d{13}$")

class Token(BaseModel):
    access_token: str
    token_type: str

class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    uploaded_at: datetime

class DownloadTokenOut(BaseModel):
    token: str
    expires_in: int

class ChatRequest(BaseModel):
    message: str

