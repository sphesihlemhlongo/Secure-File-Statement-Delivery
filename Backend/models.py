from datetime import datetime
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    id_selector: str
    id_hash: str
    created_at: datetime

class Document(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    filename: str
    filepath: str
    owner_id: int
    uploaded_at: datetime
