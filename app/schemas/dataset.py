from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class DatasetMetadataSchema(BaseModel):
    rows_count: int
    columns_count: int
    missing_ratio: float
    size_mb: float

    class Config:
        orm_mode = True

class CleanOptions(BaseModel):
    drop_duplicates: bool = True
    fill_missing: Optional[str] = "drop"  # Options: "drop", "mean", "zeros", or None

class DatasetResponse(BaseModel):
    id: int
    user_id: int
    name: str
    original_filename: str
    status: str
    raw_file_path: Optional[str]
    processed_file_path: Optional[str]
    created_at: datetime
    metadata_info: Optional[DatasetMetadataSchema]

    class Config:
        orm_mode = True

class UploadResponse(BaseModel):
    message: str
    dataset: DatasetResponse
