from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import LoanResponse
from app.models.entities import Loan, Resource, StudentProfile, User
from app.routers.dependencies import get_current_user
from app.services import loan_service, qr_service

router = APIRouter(prefix="/loans", tags=["Loans & Handover"])

@router.get("", response_model=List[LoanResponse])
def get_user_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loans = db.query(Loan).filter(
        (Loan.borrower_id == current_user.user_id) | (Loan.owner_id == current_user.user_id)
    ).all()

    results = []
    for loan in loans:
        resource = db.query(Resource).filter(Resource.resource_id == loan.resource_id).first()
        borrower_profile = db.query(StudentProfile).filter(StudentProfile.user_id == loan.borrower_id).first()
        owner_profile = db.query(StudentProfile).filter(StudentProfile.user_id == loan.owner_id).first()

        results.append(LoanResponse(
            loan_id=loan.loan_id,
            request_id=loan.request_id,
            resource_id=loan.resource_id,
            resource_name=resource.name if resource else "Resource",
            borrower_id=loan.borrower_id,
            borrower_name=borrower_profile.full_name if borrower_profile else "Borrower",
            owner_id=loan.owner_id,
            owner_name=owner_profile.full_name if owner_profile else "Owner",
            start_date=loan.start_date,
            end_date=loan.end_date,
            status=loan.status
        ))

    return results

@router.post("/{loan_id}/handover/qr")
def generate_qr(
    loan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if current_user.user_id not in [loan.borrower_id, loan.owner_id]:
        raise HTTPException(status_code=403, detail="Not authorized to access QR code for this loan")

    return qr_service.generate_handover_token(db, loan_id)

@router.post("/{loan_id}/handover/verify")
def verify_handover(
    loan_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    handover_token = payload.get("handover_token")
    if not handover_token:
        raise HTTPException(status_code=400, detail="handover_token is required")
    
    updated_loan = qr_service.verify_and_complete_handover(db, handover_token, current_user.user_id, expected_loan_id=loan_id)
    return {
        "success": True,
        "loan_id": updated_loan.loan_id,
        "status": updated_loan.status,
        "message": "QR Handover successfully verified. Loan is now ACTIVE."
    }

@router.post("/{loan_id}/cancel")
def cancel_loan(
    loan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updated_loan = loan_service.cancel_loan(db, loan_id, current_user.user_id)
    return {
        "success": True,
        "loan_id": updated_loan.loan_id,
        "status": updated_loan.status,
        "message": "Loan reservation cancelled."
    }

@router.post("/{loan_id}/return/request")
def request_return(
    loan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updated_loan = loan_service.request_loan_return(db, loan_id, current_user.user_id)
    return {
        "success": True,
        "loan_id": updated_loan.loan_id,
        "status": updated_loan.status,
        "message": "Return request sent to resource owner."
    }

@router.post("/{loan_id}/return/confirm")
def confirm_return(
    loan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updated_loan = loan_service.confirm_loan_return(db, loan_id, current_user.user_id)
    return {
        "success": True,
        "loan_id": updated_loan.loan_id,
        "status": updated_loan.status,
        "message": "Return confirmed. Loan completed."
    }
