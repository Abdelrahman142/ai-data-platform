from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import pandas as pd

from app.database import get_db
from app.models.user import User
from app.models.dataset import Dataset, DatasetShare, ActivityLog
from app.auth.dependencies import get_current_user
from app.schemas.ai import AIQueryRequest, AIQueryResponse, AIExportRequest, AISpecializedRequest
from app.utils.ai_helper import format_dataset_for_ai, call_external_ai_api, run_predictive_forecast
from app.utils.pdf_helper import generate_pdf_from_markdown
from app.api.dataset import load_dataframe
from fastapi_cache.decorator import cache

router = APIRouter()

@router.post("/query", response_model=AIQueryResponse)
@cache(expire=3600)
async def query_ai(
    request: AIQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Ownership or Sharing check
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == request.dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    # 2. Get the file path (prefer processed, fallback to raw)
    file_path = dataset.processed_file_path or dataset.raw_file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Dataset file is missing")

    try:
        # 3. Load data
        df = load_dataframe(file_path)
        data_str = format_dataset_for_ai(df)

        # 4. Call integrated AI model
        lang_full = "Arabic" if request.language == "ar" else "English"
        
        ai_response = await call_external_ai_api(
            data_str, 
            request.user_prompt, 
            model_name=request.model_name, 
            reasoning=request.reasoning,
            language=lang_full
        )

        db.add(ActivityLog(user_id=current_user.id, action="ai_query", details=f"Custom AI query on dataset {dataset.name}"))
        db.commit()

        return AIQueryResponse(response=ai_response, status="success")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Processing failed: {str(e)}")

@router.post("/summarize", response_model=AIQueryResponse)
async def summarize_dataset(
    request: AISpecializedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == request.dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = dataset.processed_file_path or dataset.raw_file_path
    df = load_dataframe(file_path)
    data_str = format_dataset_for_ai(df)
    
    prompt = "Please provide a comprehensive executive summary of this dataset. Include structure, key observations, and data quality highlights."
    lang_full = "Arabic" if request.language == "ar" else "English"
    
    response = await call_external_ai_api(data_str, prompt, model_name=request.model_name, reasoning=False, language=lang_full)
    
    db.add(ActivityLog(user_id=current_user.id, action="ai_summary", details=f"Auto-summary for dataset {dataset.name}"))
    db.commit()
    
    return AIQueryResponse(response=response, status="success")

@router.post("/analyze-anomalies", response_model=AIQueryResponse)
async def analyze_anomalies(
    request: AISpecializedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == request.dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = dataset.processed_file_path or dataset.raw_file_path
    df = load_dataframe(file_path)
    data_str = format_dataset_for_ai(df)
    
    prompt = "Analyze this dataset for statistical anomalies, outliers, and unexpected patterns. Point out specific areas that look suspicious or unusual."
    lang_full = "Arabic" if request.language == "ar" else "English"
    
    response = await call_external_ai_api(data_str, prompt, model_name=request.model_name, reasoning=True, language=lang_full)
    
    db.add(ActivityLog(user_id=current_user.id, action="ai_anomaly", details=f"Anomaly detection for dataset {dataset.name}"))
    db.commit()
    
    return AIQueryResponse(response=response, status="success")

@router.post("/correlation", response_model=AIQueryResponse)
async def analyze_correlation(
    request: AISpecializedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == request.dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = dataset.processed_file_path or dataset.raw_file_path
    df = load_dataframe(file_path)
    data_str = format_dataset_for_ai(df)
    
    prompt = "Perform a detailed correlation analysis. Identify how different columns influence each other and highlight the strongest relationships found in the data."
    lang_full = "Arabic" if request.language == "ar" else "English"
    
    response = await call_external_ai_api(data_str, prompt, model_name=request.model_name, reasoning=True, language=lang_full)
    
    db.add(ActivityLog(user_id=current_user.id, action="ai_correlation", details=f"Correlation analysis for dataset {dataset.name}"))
    db.commit()
    
    return AIQueryResponse(response=response, status="success")

@router.post("/forecast", response_model=AIQueryResponse)
async def predict_forecast(
    request: AISpecializedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == request.dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = dataset.processed_file_path or dataset.raw_file_path
    df = load_dataframe(file_path)
    data_str = format_dataset_for_ai(df)
    
    lang_full = "Arabic" if request.language == "ar" else "English"
    
    # Use the specialized forecasting function
    response = await run_predictive_forecast(
        data_str, 
        user_prompt="Generated predictive forecast", 
        model_name=request.model_name, 
        reasoning=True, 
        language=lang_full
    )
    
    db.add(ActivityLog(user_id=current_user.id, action="ai_forecast", details=f"Predictive forecast for dataset {dataset.name}"))
    db.commit()
    
    return AIQueryResponse(response=response, status="success")

@router.post("/export-pdf")
async def export_pdf(
    request: AIExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    try:
        file_path = generate_pdf_from_markdown(request.markdown_text, request.filename)
        
        # Add a task to delete the file after it's sent
        background_tasks.add_task(os.remove, file_path)
        
        return FileResponse(
            path=file_path, 
            filename=request.filename, 
            media_type='application/pdf'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
