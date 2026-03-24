from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class DatasetShareRequest(BaseModel):
    dataset_id: int
    email: EmailStr
    permission: str = "view"  # view, edit

class DatasetShareResponse(BaseModel):
    id: int
    dataset_id: int
    user_id: int
    email: str
    permission: str
    shared_at: datetime

    class Config:
        from_attributes = True

class SharedDatasetListItem(BaseModel):
    id: int
    name: str
    owner_email: str
    permission: str
    shared_at: datetime

    class Config:
        from_attributes = True

class ActivityLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    details: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

class ActivityLogListResponse(BaseModel):
    logs: List[ActivityLogResponse]
