from datetime import date, datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.entities import Loan, Notification, AuditLog, Resource

def request_loan_return(db: Session, loan_id: str, current_user_id: str) -> Loan:
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan record not found")

    if loan.borrower_id != current_user_id:
        raise HTTPException(status_code=403, detail="Only borrower can initiate return request")

    if loan.status not in ["HANDED_OVER", "ACTIVE"]:
        raise HTTPException(status_code=400, detail=f"Cannot request return for loan in '{loan.status}' status")

    loan.status = "RETURN_REQUESTED"
    db.commit()

    # Notify Owner
    notif = Notification(
        user_id=loan.owner_id,
        title="Return Requested",
        message="The borrower has marked the item as returned. Please inspect and confirm receipt."
    )
    db.add(notif)
    db.commit()

    return loan

def confirm_loan_return(db: Session, loan_id: str, current_user_id: str) -> Loan:
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan record not found")

    if loan.owner_id != current_user_id:
        raise HTTPException(status_code=403, detail="Only the resource owner can confirm item return")

    if loan.status not in ["HANDED_OVER", "ACTIVE", "RETURN_REQUESTED", "OVERDUE"]:
        raise HTTPException(status_code=400, detail=f"Cannot confirm return for loan in '{loan.status}' status")

    loan.status = "RETURNED"

    # Reset resource availability
    resource = db.query(Resource).filter(Resource.resource_id == loan.resource_id).first()
    if resource:
        resource.availability_status = "AVAILABLE"

    db.commit()

    # Notify Borrower
    notif = Notification(
        user_id=loan.borrower_id,
        title="Loan Return Confirmed",
        message="The owner has confirmed receipt of the item. Thank you for using CampusLoop!"
    )
    db.add(notif)

    # Audit log
    audit = AuditLog(
        user_id=current_user_id,
        action="LOAN_RETURNED_CONFIRMED",
        entity_type="LOAN",
        entity_id=loan_id,
        details="Loan completed successfully."
    )
    db.add(audit)
    db.commit()

    return loan

def cancel_loan(db: Session, loan_id: str, current_user_id: str) -> Loan:
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan record not found")

    if current_user_id not in [loan.borrower_id, loan.owner_id]:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this loan")

    if loan.status not in ["RESERVED"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel loan in '{loan.status}' state")

    loan.status = "CANCELLED"
    resource = db.query(Resource).filter(Resource.resource_id == loan.resource_id).first()
    if resource:
        resource.availability_status = "AVAILABLE"

    db.commit()

    audit = AuditLog(
        user_id=current_user_id,
        action="LOAN_CANCELLED",
        entity_type="LOAN",
        entity_id=loan_id,
        details="Reserved loan cancelled."
    )
    db.add(audit)
    db.commit()

    return loan

def check_and_update_overdue_loans(db: Session) -> int:
    today = date.today()
    overdue_loans = db.query(Loan).filter(
        Loan.end_date < today,
        Loan.status.in_(["HANDED_OVER", "ACTIVE", "RETURN_REQUESTED"])
    ).all()

    count = 0
    for loan in overdue_loans:
        loan.status = "OVERDUE"
        notif = Notification(
            user_id=loan.borrower_id,
            title="LOAN OVERDUE WARNING",
            message=f"Your loan for item ended on {loan.end_date}. Please return it immediately to avoid penalties."
        )
        db.add(notif)
        count += 1

    if count > 0:
        db.commit()
    return count
