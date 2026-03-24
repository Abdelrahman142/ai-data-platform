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

class ProcessingLogSchema(BaseModel):
    step_name: str
    status: str
    message: Optional[str]
    timestamp: datetime

    class Config:
        orm_mode = True

class CleanOptions(BaseModel):
    drop_duplicates: bool = True
    fill_missing: Optional[str] = "drop"  # Options: "drop", "mean", "zeros", or None
    ai_rename: bool = False

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
    permission: str = "owner"
    logs: List[ProcessingLogSchema] = []

    class Config:
        orm_mode = True

class UploadResponse(BaseModel):
    message: str
    dataset: DatasetResponse

class DatasetStats(BaseModel):
    numerical: dict
    categorical: dict
    smart_kpis: Optional[dict] = {}
    smart_charts: Optional[dict] = {}

class UpdateCellRequest(BaseModel):
    row_index: int
    column_name: str
    new_value: str
