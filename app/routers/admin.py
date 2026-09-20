from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import User, Resource, Loan, Report, AuditLog, StudentProfile
from app.routers.dependencies import get_current_admin
from app.services import moderation_service

router = APIRouter(prefix="/admin", tags=["Admin & Moderation"])

@router.get("/dashboard")
def get_admin_dashboard_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_students = db.query(User).filter(User.role == "STUDENT").count()
    total_resources = db.query(Resource).filter(Resource.deleted_at.is_(None)).count()
    active_loans = db.query(Loan).filter(Loan.status.in_(["HANDED_OVER", "ACTIVE"])).count()
    overdue_loans = db.query(Loan).filter(Loan.status == "OVERDUE").count()
    open_reports = db.query(Report).filter(Report.status == "OPEN").count()

    return {
        "total_students": total_students,
        "total_resources": total_resources,
        "active_loans": active_loans,
        "overdue_loans": overdue_loans,
        "open_reports": open_reports
    }

@router.get("/users")
def list_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    results = []
    for u in users:
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == u.user_id).first()
        results.append({
            "user_id": u.user_id,
            "email": u.email,
            "full_name": profile.full_name if profile else "N/A",
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at
        })
    return results

from app.services import moderation_service, loan_service

@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: str,
    payload: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    reason = payload.get("reason", "Violated campus platform terms")
    user = moderation_service.suspend_user(db, admin.user_id, user_id, reason)
    return {"message": f"User {user.email} suspended successfully"}

@router.post("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = moderation_service.reactivate_user(db, admin.user_id, user_id)
    return {"message": f"User {user.email} reactivated successfully"}

@router.post("/overdue-check")
def trigger_overdue_check(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    updated_count = loan_service.check_and_update_overdue_loans(db)
    return {"message": f"Overdue loan check completed. {updated_count} loan(s) updated to OVERDUE."}

@router.get("/reports")
def list_reports(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    reports = db.query(Report).all()
    return reports

@router.post("/reports/{report_id}/resolve")
def resolve_report(
    report_id: str,
    payload: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    new_status = payload.get("status", "RESOLVED")
    action_taken = payload.get("action_taken", "Reviewed and resolved by admin")
    report = moderation_service.resolve_report(db, admin.user_id, report_id, new_status, action_taken)
    return {"message": f"Report {report.report_id} updated to {report.status}"}

@router.get("/audit-logs")
def get_audit_logs(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return logs
