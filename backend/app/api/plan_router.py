from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_token_payload
from app.models.plan import Plan
from app.schemas.plan_schema import PlanUpdate, PlanResponse
from typing import List
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(prefix="/api/v1/plans", tags=["Plans History"])

@router.get("", response_model=List[PlanResponse])
def get_all_plans(
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_token_payload)
):
    org_id = token_payload.get("org_id")
    # Fetch only plans belonging to this tenant organization
    plans = db.query(Plan).filter(Plan.organization_id == org_id).order_by(Plan.created_at.desc()).all()
    return plans

@router.get("/{plan_id}", response_model=PlanResponse)
def get_single_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_token_payload)
):
    org_id = token_payload.get("org_id")
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.organization_id == org_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or access denied.")
    return plan

@router.put("/{plan_id}", response_model=PlanResponse)
def rename_plan(
    plan_id: int, 
    plan_data: PlanUpdate, 
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_token_payload)
):
    org_id = token_payload.get("org_id")
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.organization_id == org_id).first()
    
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or access denied.")
    
    clean_title = plan_data.title.strip()
    if not clean_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan title cannot be empty.")
        
    plan.title = clean_title
    
    try:
        db.commit()
        db.refresh(plan)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error occurred while updating the plan.")
        
    return plan

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int, 
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_token_payload)
):
    org_id = token_payload.get("org_id")
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.organization_id == org_id).first()
    
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or access denied.")
        
    try:
        db.delete(plan)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error occurred while deleting the plan.")
        
    return None