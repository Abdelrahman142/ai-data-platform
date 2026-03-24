import os
import shutil
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.dataset import Dataset, DatasetMetadata, ProcessingLog, DatasetShare, ActivityLog
from app.schemas.dataset import UploadResponse, DatasetResponse, CleanOptions, DatasetStats, UpdateCellRequest
from app.auth.dependencies import get_current_user

from app.utils.ai_helper import analyze_and_rename_columns
from fastapi_cache.decorator import cache
import numpy as np

def load_dataframe(file_path: str) -> pd.DataFrame:
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext == '.csv':
        return pd.read_csv(file_path, encoding='utf-8-sig')
    elif file_ext in {'.xlsx', '.xls'}:
        try:
            return pd.read_excel(file_path)
        except ValueError:
            return pd.read_csv(file_path, encoding='utf-8-sig')
    else:
        try:
            return pd.read_csv(file_path, encoding='utf-8-sig')
        except Exception:
            raise ValueError(f"Unsupported file format: {file_ext}")

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
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Load Raw Data robustly
        df = load_dataframe(file_path)
        if file_ext != '.csv':
            # Standardize column names immediately for Excel to avoid index/naming issues
            df.columns = [str(c) for c in df.columns]
        
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

        # 3. Data Transformation (Basic)
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
        df.to_csv(processed_path, index=False, encoding='utf-8-sig')
        
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
        
        db.add(ActivityLog(user_id=current_user.id, action="upload", details=f"Uploaded dataset {file.filename}"))
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
@cache(expire=60)
def get_user_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Datasets owned by user
    owned_datasets = db.query(Dataset).filter(Dataset.user_id == current_user.id).all()
    for d in owned_datasets:
        d.permission = "owner"
    
    # Datasets shared with user
    shared_entries = db.query(DatasetShare).filter(DatasetShare.user_id == current_user.id).all()
    shared_datasets = []
    for s in shared_entries:
        d = s.dataset
        d.permission = s.permission
        shared_datasets.append(d)
    
    return owned_datasets + shared_datasets

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check ownership or sharing
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")
    return dataset

@router.post("/{dataset_id}/clean", response_model=DatasetResponse)
async def clean_dataset(
    dataset_id: int, 
    options: CleanOptions, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Must be owner or have 'edit' permission
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    share = db.query(DatasetShare).filter(DatasetShare.dataset_id == dataset_id, DatasetShare.user_id == current_user.id).first()
    has_edit_perm = share and share.permission == "edit"
    
    if not is_owner and not has_edit_perm:
        raise HTTPException(status_code=403, detail="You do not have permission to clean this dataset")
    
    if not dataset.raw_file_path or not os.path.exists(dataset.raw_file_path):
        raise HTTPException(status_code=400, detail="Raw dataset file is missing")

    try:
        # Load Raw Data robustly
        file_ext = os.path.splitext(dataset.raw_file_path)[1].lower()
        df = load_dataframe(dataset.raw_file_path)
        if file_ext != '.csv':
            # Standardize column names for Excel
            df.columns = [str(c) for c in df.columns]
        
        # 1. AI Auto-Rename (Optional)
        if options.ai_rename:
            df = await analyze_and_rename_columns(df)
            processing_log = ProcessingLog(
                dataset_id=dataset.id,
                step_name="ai_renaming",
                status="completed",
                message="AI identified and renamed cryptic columns."
            )
            db.add(processing_log)

        # 2. Apply cleaning operations
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
        df.to_csv(processed_path, index=False, encoding='utf-8-sig')

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
        db.add(ActivityLog(user_id=current_user.id, action="clean", details=f"Cleaned dataset {dataset.name}"))
        
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
    format: str = "csv",
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.add(ActivityLog(user_id=current_user.id, action="export", details=f"Exported dataset {dataset.name} as {format}"))
    db.commit()

    file_path = dataset.processed_file_path if type == "processed" else dataset.raw_file_path
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail=f"Requested {type} file is not available")
        
    try:
        df = load_dataframe(file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    if format == "json":
        json_path = file_path.replace(".csv", ".json")
        df.to_json(json_path, orient="records", indent=4)
        return FileResponse(path=json_path, filename=os.path.basename(json_path), media_type='application/json')
    
    elif format == "excel":
        excel_path = file_path.replace(".csv", ".xlsx")
        df.to_excel(excel_path, index=False, engine='openpyxl')
        return FileResponse(path=excel_path, filename=os.path.basename(excel_path), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
    return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type='text/csv')

@router.get("/{dataset_id}/preview")
def preview_dataset(
    dataset_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")
        
    file_path = dataset.processed_file_path or dataset.raw_file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Dataset file not available")

    try:
        df = load_dataframe(file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unsupported or corrupted file: {str(e)}")
    # Return first 50 rows for preview
    preview_data = df.head(50).to_dict(orient="records")
    return {"columns": df.columns.tolist(), "data": preview_data}

@router.patch("/{dataset_id}/update-cell")
def update_cell(
    dataset_id: int,
    request: UpdateCellRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    share = db.query(DatasetShare).filter(DatasetShare.dataset_id == dataset_id, DatasetShare.user_id == current_user.id).first()
    has_edit_perm = share and share.permission == "edit"
    
    if not is_owner and not has_edit_perm:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this dataset")
        
    file_path = dataset.processed_file_path or dataset.raw_file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Dataset file not available")

    try:
        df = load_dataframe(file_path)
        if request.row_index >= len(df) or request.row_index < 0:
            raise HTTPException(status_code=400, detail="Invalid row index")
        
        if request.column_name not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{request.column_name}' not found")

        # Try to cast if numeric
        original_val = df.at[request.row_index, request.column_name]
        try:
            if isinstance(original_val, (int, np.integer)):
                df.at[request.row_index, request.column_name] = int(request.new_value)
            elif isinstance(original_val, (float, np.floating)):
                df.at[request.row_index, request.column_name] = float(request.new_value)
            else:
                df.at[request.row_index, request.column_name] = request.new_value
        except ValueError:
            df.at[request.row_index, request.column_name] = request.new_value

        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        # Log the change
        db.add(ProcessingLog(
            dataset_id=dataset.id,
            step_name="manual_edit",
            status="completed",
            message=f"Updated cell at row {request.row_index}, column '{request.column_name}'"
        ))
        db.add(ActivityLog(
            user_id=current_user.id,
            action="edit",
            details=f"Updated cell in dataset {dataset.name} (row {request.row_index}, col {request.column_name})"
        ))
        db.commit()
        
        return {"message": "Cell updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating cell: {str(e)}")

@router.get("/{dataset_id}/stats", response_model=DatasetStats)
def get_dataset_stats(
    dataset_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    is_owner = dataset.user_id == current_user.id
    is_shared = db.query(DatasetShare).filter(DatasetShare.dataset_id == dataset_id, DatasetShare.user_id == current_user.id).first()
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=403, detail="Access denied")
        
    file_path = dataset.processed_file_path or dataset.raw_file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Dataset file not available")

    try:
        df = load_dataframe(file_path)
        
        stats = {"numerical": {}, "categorical": {}}

        # Numerical columns analysis
        num_cols = df.select_dtypes(include=['number']).columns
        for col in num_cols:
            col_data = df[col].replace([np.inf, -np.inf], np.nan).dropna()
            if not col_data.empty:
                # Basic stats + histogram bins
                hist, bin_edges = np.histogram(col_data, bins=10)
                stats["numerical"][str(col)] = {
                    "min": float(col_data.min()) if not pd.isna(col_data.min()) else 0.0,
                    "max": float(col_data.max()) if not pd.isna(col_data.max()) else 0.0,
                    "mean": float(col_data.mean()) if not pd.isna(col_data.mean()) else 0.0,
                    "histogram": {
                        "counts": hist.tolist(),
                        "bins": [float(b) for b in bin_edges.tolist()]
                    }
                }

        # Categorical columns analysis
        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in cat_cols:
            val_counts = df[col].astype(str).value_counts().head(10)
            stats["categorical"][str(col)] = val_counts.to_dict()

        # --- SMART DASHBOARD HEURISTICS ---
        # 1. Identify potential Date columns
        date_col = None
        for col in df.columns:
            if any(term in str(col).lower() for term in ['date', 'day', 'month', 'year', 'time']):
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    date_col = col
                    break
                except:
                    pass
        
        # 2. Identify potential KPI columns
        sales_col = next((c for c in num_cols if any(x in str(c).lower() for x in ['sale', 'revenue', 'total'])), None)
        profit_col = next((c for c in num_cols if 'profit' in str(c).lower() or 'margin' in str(c).lower()), None)
        cost_col = next((c for c in num_cols if 'cost' in str(c).lower() or 'expense' in str(c).lower()), None)
        
        # 3. Identify product/customer/supplier columns
        product_col = next((c for c in cat_cols if 'product' in str(c).lower() or 'item' in str(c).lower() or 'medicine' in str(c).lower() or 'drug' in str(c).lower()), None)
        supplier_col = next((c for c in cat_cols if 'supplier' in str(c).lower() or 'vendor' in str(c).lower() or 'brand' in str(c).lower()), None)
        customer_col = next((c for c in cat_cols if 'customer' in str(c).lower() or 'client' in str(c).lower() or 'pharmacy' in str(c).lower()), None)

        # Fallbacks if specific terms not found
        if not product_col and len(cat_cols) > 0:
            product_col = cat_cols[0]
        if not sales_col and len(num_cols) > 0:
            sales_col = num_cols[0]

        smart_kpis = {}
        smart_charts = {}

        def safe_float(val):
            if pd.isna(val) or np.isinf(val): return 0.0
            return float(val)

        # Build KPIs
        if sales_col:
            smart_kpis['total_sales'] = safe_float(df[sales_col].sum())
        if cost_col:
            smart_kpis['total_cost'] = safe_float(df[cost_col].sum())
        if profit_col:
            smart_kpis['total_profit'] = safe_float(df[profit_col].sum())
        elif sales_col and cost_col:
            smart_kpis['total_profit'] = safe_float(df[sales_col].sum() - df[cost_col].sum())
        
        if 'total_profit' in smart_kpis and 'total_sales' in smart_kpis and smart_kpis['total_sales'] > 0:
            smart_kpis['profit_margin'] = safe_float((smart_kpis['total_profit'] / smart_kpis['total_sales']) * 100)

        # Build Smart Charts
        if date_col and sales_col:
            # Sales Trend (monthly aggregation)
            df_trend = df.copy()
            # Drop NaT dates
            df_trend = df_trend.dropna(subset=[date_col])
            if not df_trend.empty:
                df_trend['Month'] = df_trend[date_col].dt.to_period('M').astype(str)
                trend_data = df_trend.groupby('Month')[sales_col].sum().reset_index()
                smart_charts['sales_trend'] = {
                    'labels': trend_data['Month'].tolist()[-12:], # Last 12 months
                    'data': [safe_float(v) for v in trend_data[sales_col].tolist()[-12:]]
                }
                if profit_col:
                     profit_trend = df_trend.groupby('Month')[profit_col].sum().reset_index()
                     smart_charts['sales_trend']['profit_data'] = [safe_float(v) for v in profit_trend[profit_col].tolist()[-12:]]

        if product_col and sales_col:
            top_products = df.groupby(product_col)[sales_col].sum().nlargest(10).reset_index()
            smart_charts['top_products'] = {
                'labels': [str(x) for x in top_products[product_col].tolist()],
                'data': [safe_float(v) for v in top_products[sales_col].tolist()]
            }
        
        if customer_col and sales_col:
            top_customers = df.groupby(customer_col)[sales_col].sum().nlargest(10).reset_index()
            smart_charts['top_customers'] = {
                'labels': [str(x) for x in top_customers[customer_col].tolist()],
                'data': [safe_float(v) for v in top_customers[sales_col].tolist()]
            }
            
        if supplier_col and (cost_col or sales_col):
            target_metric = cost_col if cost_col else sales_col
            top_suppliers = df.groupby(supplier_col)[target_metric].sum().nlargest(10).reset_index()
            smart_charts['top_suppliers'] = {
                'labels': [str(x) for x in top_suppliers[supplier_col].tolist()],
                'data': [safe_float(v) for v in top_suppliers[target_metric].tolist()],
                'metric_name': 'Cost' if cost_col else 'Sales'
            }

        stats['smart_kpis'] = smart_kpis
        stats['smart_charts'] = smart_charts

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating stats: {str(e)}")
