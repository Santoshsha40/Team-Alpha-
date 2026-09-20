from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.entities import BorrowRequest, Resource, Loan, Notification
from app.schemas.schemas import BorrowRequestCreate
from app.services.availability_service import is_resource_available
from app.services.qr_service import generate_handover_token

def create_borrow_request(db: Session, borrower_id: str, request_data: BorrowRequestCreate) -> BorrowRequest:
    resource = db.query(Resource).filter(
        Resource.resource_id == request_data.resource_id,
        Resource.deleted_at.is_(None)
    ).first()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found or unavailable")

    # Rule 1: A student cannot borrow their own resource
    if resource.owner_id == borrower_id:
        raise HTTPException(status_code=400, detail="You cannot borrow your own listed resource")

    # Rule 3: Check availability & double booking
    if not is_resource_available(db, resource.resource_id, request_data.requested_from, request_data.requested_until):
        raise HTTPException(
            status_code=400,
            detail="Resource is not available for the requested date range. Overlapping reservation exists."
        )

    new_request = BorrowRequest(
        resource_id=resource.resource_id,
        borrower_id=borrower_id,
        owner_id=resource.owner_id,
        requested_from=request_data.requested_from,
        requested_until=request_data.requested_until,
        message=request_data.message,
        status="PENDING"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Send Notification to Owner
    notif = Notification(
        user_id=resource.owner_id,
        title="New Borrow Request Received",
        message=f"A student requested your '{resource.name}' from {request_data.requested_from} to {request_data.requested_until}."
    )
    db.add(notif)
    db.commit()

    return new_request

def accept_borrow_request(db: Session, request_id: str, current_user_id: str) -> dict:
    request_obj = db.query(BorrowRequest).filter(BorrowRequest.request_id == request_id).first()
    if not request_obj:
        raise HTTPException(status_code=404, detail="Borrow request not found")

    # Rule 4: Only owner can accept/reject
    if request_obj.owner_id != current_user_id:
        raise HTTPException(status_code=403, detail="Only the resource owner can accept this request")

    if request_obj.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is already in '{request_obj.status}' status")

    # Re-verify availability
    if not is_resource_available(db, request_obj.resource_id, request_obj.requested_from, request_obj.requested_until):
        request_obj.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="Resource was reserved by another request for these dates")

    request_obj.status = "ACCEPTED"

    # Update Resource Availability
    resource = db.query(Resource).filter(Resource.resource_id == request_obj.resource_id).first()
    if resource:
        resource.availability_status = "RESERVED"

    # Create Loan Record in RESERVED state
    loan = Loan(
        request_id=request_obj.request_id,
        resource_id=request_obj.resource_id,
        borrower_id=request_obj.borrower_id,
        owner_id=request_obj.owner_id,
        start_date=request_obj.requested_from,
        end_date=request_obj.requested_until,
        status="RESERVED"
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    # Generate Handover QR token
    token_data = generate_handover_token(db, loan.loan_id)

    # Notification to Borrower
    notif = Notification(
        user_id=request_obj.borrower_id,
        title="Borrow Request Accepted!",
        message=f"Your request for item was ACCEPTED! Meet the owner to scan the Handover QR code."
    )
    db.add(notif)
    db.commit()

    return {
        "request_id": request_obj.request_id,
        "status": request_obj.status,
        "loan": {
            "loan_id": loan.loan_id,
            "status": loan.status,
            "handover_token": token_data["token"],
            "qr_code_url": token_data["qr_code_url"]
        }
    }

def reject_borrow_request(db: Session, request_id: str, current_user_id: str) -> BorrowRequest:
    request_obj = db.query(BorrowRequest).filter(BorrowRequest.request_id == request_id).first()
    if not request_obj:
        raise HTTPException(status_code=404, detail="Borrow request not found")

    if request_obj.owner_id != current_user_id:
        raise HTTPException(status_code=403, detail="Only owner can reject this request")

    request_obj.status = "REJECTED"
    db.commit()

    notif = Notification(
        user_id=request_obj.borrower_id,
        title="Request Rejected",
        message=f"Your borrow request for resource was rejected by the owner."
    )
    db.add(notif)
    db.commit()

    return request_obj

def cancel_borrow_request(db: Session, request_id: str, current_user_id: str) -> BorrowRequest:
    request_obj = db.query(BorrowRequest).filter(BorrowRequest.request_id == request_id).first()
    if not request_obj:
        raise HTTPException(status_code=404, detail="Borrow request not found")

    if request_obj.borrower_id != current_user_id:
        raise HTTPException(status_code=403, detail="Only the borrower can cancel this request")

    if request_obj.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Cannot cancel request in '{request_obj.status}' status")

    request_obj.status = "CANCELLED"
    db.commit()

    return request_obj
