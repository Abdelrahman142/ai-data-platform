from pydantic import BaseModel
from typing import Optional

class AIQueryRequest(BaseModel):
    dataset_id: int
    user_prompt: str
    model_name: Optional[str] = "nemotron-3-nano:30b-cloud"
    reasoning: Optional[bool] = True
    language: Optional[str] = "en"

class AIQueryResponse(BaseModel):
    response: str
    status: str

class AIExportRequest(BaseModel):
    markdown_text: str
    filename: Optional[str] = "AI_Report.pdf"

class AISpecializedRequest(BaseModel):
    dataset_id: int
    model_name: Optional[str] = "nemotron-3-nano:30b-cloud"
    language: Optional[str] = "en"
