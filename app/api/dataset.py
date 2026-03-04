import os
import shutil
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.dataset import Dataset, DatasetMetadata, ProcessingLog
from app.schemas.dataset import UploadResponse, DatasetResponse, CleanOptions
from app.auth.dependencies import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
CLEAN_DIR = "cleaned"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CLEAN_DIR, exist_ok=True)

@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Load Raw Data
        df = pd.read_csv(file_path)
        
        # 1. Data Validation
        if df.shape[0] == 0 or df.shape[1] == 0:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="Uploaded file is empty or corrupted.")
        
        new_dataset = Dataset(
            user_id=current_user.id,
            name=file.filename,
            original_filename=file.filename,
            status="processing",
            raw_file_path=file_path
        )
        db.add(new_dataset)
        db.flush() # Secure dataset ID
        
        db.add(ProcessingLog(dataset_id=new_dataset.id, step_name="validation", status="completed", message="Data dimensions verified."))
        
        # 2. Data Cleaning
        df = df.drop_duplicates()
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
        object_cols = df.select_dtypes(include=['object']).columns
        df[object_cols] = df[object_cols].fillna("Unknown")
        
        db.add(ProcessingLog(dataset_id=new_dataset.id, step_name="cleaning", status="completed", message="Auto-dropped duplicates and filled nulls."))

        # 3. Data Transformation
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace(r'[^\w\s]', '', regex=True)
        db.add(ProcessingLog(dataset_id=new_dataset.id, step_name="transformation", status="completed", message="Standardized column headers."))

        # 4. Quality Check
        if df.shape[0] == 0:
            db.add(ProcessingLog(dataset_id=new_dataset.id, step_name="quality_check", status="failed", message="Quality check failed post-process."))
            db.commit()
            raise HTTPException(status_code=400, detail="Data was fully expunged post-cleaning due to low quality.")
            
        db.add(ProcessingLog(dataset_id=new_dataset.id, step_name="quality_check", status="completed", message="Quality check passed!"))

        # Save the automatically processed dataset
        processed_filename = f"auto_cleaned_{file.filename}"
        processed_path = os.path.join(CLEAN_DIR, processed_filename)
        df.to_csv(processed_path, index=False)
        
        # Finalize Mapping 
        new_dataset.status = "ready"
        new_dataset.processed_file_path = processed_path
        
        rows_count = df.shape[0]
        columns_count = df.shape[1]
        missing_ratio = float(df.isnull().sum().sum() / (rows_count * columns_count)) if rows_count > 0 else 0.0
        size_mb = os.path.getsize(processed_path) / (1024 * 1024)
        
        new_metadata = DatasetMetadata(
            dataset_id=new_dataset.id,
            rows_count=rows_count,
            columns_count=columns_count,
            missing_ratio=missing_ratio,
            size_mb=size_mb
        )
        db.add(new_metadata)
        
        db.commit()
        db.refresh(new_dataset)
        
        return {"message": "Dataset automatically validated, cleaned, standardized, and stored successfully!", "dataset": new_dataset}
        
    except HTTPException as htpe:
        db.rollback()
        raise htpe
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error executing automated pipeline: {str(e)}")

@router.get("/", response_model=list[DatasetResponse])
def get_user_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    datasets = db.query(Dataset).filter(Dataset.user_id == current_user.id).all()
    return datasets

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    return dataset

@router.post("/{dataset_id}/clean", response_model=DatasetResponse)
def clean_dataset(
    dataset_id: int, 
    options: CleanOptions, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
    
    if not dataset.raw_file_path or not os.path.exists(dataset.raw_file_path):
        raise HTTPException(status_code=400, detail="Raw dataset file is missing")

    try:
        df = pd.read_csv(dataset.raw_file_path)
        
        # Apply cleaning operations
        if options.drop_duplicates:
            df = df.drop_duplicates()
            
        if options.fill_missing == "drop":
            df = df.dropna()
        elif options.fill_missing == "mean":
            # Only fill mean for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
        elif options.fill_missing == "zeros":
            df = df.fillna(0)

        # Save processed dataset
        processed_filename = f"cleaned_{dataset.name}"
        processed_path = os.path.join(CLEAN_DIR, processed_filename)
        df.to_csv(processed_path, index=False)

        # Update Dataset Record
        dataset.processed_file_path = processed_path
        dataset.status = "ready"
        
        # Update Metadata
        metadata = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == dataset.id).first()
        if metadata:
            rows_count = df.shape[0]
            columns_count = df.shape[1]
            missing_ratio = float(df.isnull().sum().sum() / (rows_count * columns_count)) if rows_count > 0 else 0.0
            size_mb = os.path.getsize(processed_path) / (1024 * 1024)
            
            metadata.rows_count = rows_count
            metadata.columns_count = columns_count
            metadata.missing_ratio = missing_ratio
            metadata.size_mb = size_mb

        # Log operation
        log_msg = f"Cleaned data applied: Drop duplicates={options.drop_duplicates}, Fill missing={options.fill_missing}"
        processing_log = ProcessingLog(
            dataset_id=dataset.id,
            step_name="cleaning",
            status="completed",
            message=log_msg
        )
        db.add(processing_log)
        
        db.commit()
        db.refresh(dataset)
        return dataset

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cleaning dataset: {str(e)}")


@router.get("/{dataset_id}/download")
def download_dataset(
    dataset_id: int, 
    type: str = "processed", 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    file_path = dataset.processed_file_path if type == "processed" else dataset.raw_file_path
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail=f"Requested {type} file is not available")
        
    return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type='text/csv')

