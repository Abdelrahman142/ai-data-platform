from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.dataset import Dataset, DatasetShare, ActivityLog
from app.auth.dependencies import get_current_user
from app.schemas.collaboration import DatasetShareRequest, DatasetShareResponse, SharedDatasetListItem, ActivityLogResponse

router = APIRouter()

@router.post("/share", response_model=DatasetShareResponse)
async def share_dataset(
    request: DatasetShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify dataset ownership
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or you are not the owner")

    # 2. Find target user
    target_user = db.query(User).filter(User.email == request.email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User with this email does not exist")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot share a dataset with yourself")

    # 3. Check if already shared
    existing_share = db.query(DatasetShare).filter(
        DatasetShare.dataset_id == request.dataset_id,
        DatasetShare.user_id == target_user.id
    ).first()

    if existing_share:
        existing_share.permission = request.permission
        db.commit()
        db.refresh(existing_share)
        return existing_share

    # 4. Create new share
    new_share = DatasetShare(
        dataset_id=request.dataset_id,
        user_id=target_user.id,
        permission=request.permission
    )
    db.add(new_share)
    
    # 5. Log activity
    log = ActivityLog(
        user_id=current_user.id,
        action="share",
        details=f"Shared dataset {dataset.name} with {request.email} ({request.permission})"
    )
    db.add(log)
    
    db.commit()
    db.refresh(new_share)
    
    # Add email for response
    new_share.email = target_user.email
    return new_share

@router.get("/shared-with-me", response_model=List[SharedDatasetListItem])
async def list_shared_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shared = db.query(DatasetShare).filter(DatasetShare.user_id == current_user.id).all()
    
    results = []
    for s in shared:
        results.append({
            "id": s.dataset.id,
            "name": s.dataset.name,
            "owner_email": s.dataset.owner.email,
            "permission": s.permission,
            "shared_at": s.shared_at
        })
    return results

@router.get("/history", response_model=List[ActivityLogResponse])
async def get_activity_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logs = db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id).order_by(ActivityLog.timestamp.desc()).all()
    return logs
