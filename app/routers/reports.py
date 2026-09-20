from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import ReportCreate, ReportResponse
from app.models.entities import Report, User
from app.routers.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports & Moderation"])

@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    report_data: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = Report(
        reporter_id=current_user.user_id,
        reported_user_id=report_data.reported_user_id,
        resource_id=report_data.resource_id,
        reason=report_data.reason,
        details=report_data.details,
        status="OPEN"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return ReportResponse(
        report_id=report.report_id,
        reporter_id=report.reporter_id,
        reported_user_id=report.reported_user_id,
        resource_id=report.resource_id,
        reason=report.reason,
        details=report.details,
        status=report.status,
        created_at=report.created_at
    )
