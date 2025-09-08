# src/models.py
from pydantic import BaseModel
from typing import Optional, Dict

class Channel(BaseModel):
    id: str

class AriEvent(BaseModel):
    type: str
    channel: Optional[Channel]
