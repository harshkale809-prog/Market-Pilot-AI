import inspect
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.api.dependencies import get_current_token_payload
from app.agents.planner_crew import run_marketing_planner
from app.core.database import get_db
from app.models.plan import Plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["AI Agent"])

class PlannerRequest(BaseModel):
    goal: str = Field(..., min_length=5, description="The marketing goal or objective to plan")
    # Interactive / Adaptive survey inputs (optional for initial plan or re-plan)
    timeline: Optional[str] = Field(None, description="Timeline (e.g., '2 weeks', '1 month', 'Quarterly')")
    budget: Optional[str] = Field(None, description="Budget level (e.g., 'Low / Organic', 'Medium ($5k)', 'High')")
    target_audience: Optional[str] = Field(None, description="Target demographic / audience")
    primary_channels: Optional[str] = Field(None, description="Preferred channels (Social, Email, PR, Events)")
    
    # Adaptive re-planning fields (when deadlines are missed or scope changes)
    is_replanned: Optional[bool] = False
    missed_tasks: Optional[str] = Field(None, description="Which tasks or deadlines were missed")
    days_delayed: Optional[int] = Field(0, description="How many days behind schedule")
    adjustment_strategy: Optional[str] = Field(None, description="Strategy: 'compress' (crunch to meet original date), 'extend' (push deadlines back), or 're-prioritize' (drop low-priority tasks)")
    original_plan_summary: Optional[str] = Field(None, description="Context from previous plan to adjust")

@router.post("/plan")
async def generate_marketing_plan(
    request: PlannerRequest, 
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_token_payload)
):
    org_id = token_payload.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant context in credentials."
        )
    
    # Construct an enriched goal prompt if questionnaires / re-planning parameters are supplied
    goal_parts = [request.goal.strip()]
    
    if request.timeline:
        goal_parts.append(f"Target Timeline: {request.timeline}")
    if request.budget:
        goal_parts.append(f"Budget Level: {request.budget}")
    if request.target_audience:
        goal_parts.append(f"Target Audience: {request.target_audience}")
    if request.primary_channels:
        goal_parts.append(f"Primary Channels: {request.primary_channels}")
        
    if request.is_replanned:
        goal_parts.append("\n=== RE-PLANNING & CONTINGENCY DIRECTIVE ===")
        goal_parts.append(f"STATUS: Deadlines were missed. This is an adaptive recovery plan.")
        if request.missed_tasks:
            goal_parts.append(f"Tasks Missed/Delayed: {request.missed_tasks}")
        if request.days_delayed:
            goal_parts.append(f"Days Behind Schedule: {request.days_delayed} days")
        if request.adjustment_strategy:
            goal_parts.append(f"Recovery Strategy Chosen: {request.adjustment_strategy.upper()} - "
                              f"(e.g., recalculate remaining sprints, shift deliverables, or fast-track critical paths).")
        if request.original_plan_summary:
            goal_parts.append(f"Prior Context / Plan Being Adjusted:\n{request.original_plan_summary[:1000]}")
        goal_parts.append("Provide a revised, realistic recovery schedule highlighting adjusted deadlines, catch-up milestones, and critical path priorities.")

    composite_goal = "\n".join(goal_parts)

    try:
        # Offload synchronous CrewAI execution to threadpool so event loop is never blocked
        planner_result = await run_in_threadpool(run_marketing_planner, goal=composite_goal, org_id=org_id)
        
        # Guard against unresolved coroutine object
        if inspect.iscoroutine(planner_result):
            planner_result = await planner_result
            
        final_plan_content = str(planner_result)
        
        # Generate default descriptive title
        clean_goal = request.goal.strip()
        prefix = "Recovery Plan: " if request.is_replanned else "Strategy: "
        default_title = f"{prefix}{clean_goal[:35]}..." if len(clean_goal) > 35 else f"{prefix}{clean_goal}"
        
        # Save plan to MySQL under authenticated organization
        new_plan = Plan(
            title=default_title,
            content=final_plan_content,
            organization_id=org_id
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        
        return {
            "status": "success",
            "plan_id": new_plan.id,
            "goal": request.goal,
            "plan": final_plan_content,
            "is_replanned": request.is_replanned
        }
    except ValueError as ve:
        db.rollback()
        logger.warning(f"Planner configuration error: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        db.rollback()
        logger.error(f"AI Planner execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"The AI Agent encountered an error during execution: {str(e)}"
        )
