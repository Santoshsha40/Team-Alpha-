from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.entities import User, Resource, Report, AuditLog

def suspend_user(db: Session, admin_id: str, target_user_id: str, reason: str) -> User:
    user = db.query(User).filter(User.user_id == target_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = "SUSPENDED"
    
    audit = AuditLog(
        user_id=admin_id,
        action="USER_SUSPENDED",
        entity_type="USER",
        entity_id=target_user_id,
        details=f"Reason: {reason}"
    )
    db.add(audit)
    db.commit()
    return user

def reactivate_user(db: Session, admin_id: str, target_user_id: str) -> User:
    user = db.query(User).filter(User.user_id == target_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = "ACTIVE"
    
    audit = AuditLog(
        user_id=admin_id,
        action="USER_REACTIVATED",
        entity_type="USER",
        entity_id=target_user_id,
        details="User account reactivated by admin"
    )
    db.add(audit)
    db.commit()
    return user

def resolve_report(db: Session, admin_id: str, report_id: str, new_status: str, action_taken: str) -> Report:
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = new_status
    
    audit = AuditLog(
        user_id=admin_id,
        action="REPORT_RESOLVED",
        entity_type="REPORT",
        entity_id=report_id,
        details=f"Status changed to {new_status}. Action: {action_taken}"
    )
    db.add(audit)
    db.commit()
    return report
