from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import BorrowRequestCreate, BorrowRequestResponse
from app.models.entities import BorrowRequest, Resource, User, StudentProfile
from app.routers.dependencies import get_current_user
from app.services import borrow_service

router = APIRouter(prefix="/borrow-requests", tags=["Borrow Requests"])

@router.post("", response_model=BorrowRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    request_data: BorrowRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = borrow_service.create_borrow_request(db, current_user.user_id, request_data)
    
    resource = db.query(Resource).filter(Resource.resource_id == req.resource_id).first()
    borrower_profile = db.query(StudentProfile).filter(StudentProfile.user_id == req.borrower_id).first()
    owner_profile = db.query(StudentProfile).filter(StudentProfile.user_id == req.owner_id).first()

    return BorrowRequestResponse(
        request_id=req.request_id,
        resource_id=req.resource_id,
        resource_name=resource.name if resource else "Resource",
        borrower_id=req.borrower_id,
        borrower_name=borrower_profile.full_name if borrower_profile else "Borrower",
        owner_id=req.owner_id,
        owner_name=owner_profile.full_name if owner_profile else "Owner",
        requested_from=req.requested_from,
        requested_until=req.requested_until,
        message=req.message,
        status=req.status,
        created_at=req.created_at
    )

@router.get("", response_model=List[BorrowRequestResponse])
def get_user_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    requests = db.query(BorrowRequest).filter(
        (BorrowRequest.borrower_id == current_user.user_id) | (BorrowRequest.owner_id == current_user.user_id)
    ).all()

    results = []
    for req in requests:
        resource = db.query(Resource).filter(Resource.resource_id == req.resource_id).first()
        borrower_profile = db.query(StudentProfile).filter(StudentProfile.user_id == req.borrower_id).first()
        owner_profile = db.query(StudentProfile).filter(StudentProfile.user_id == req.owner_id).first()

        results.append(BorrowRequestResponse(
            request_id=req.request_id,
            resource_id=req.resource_id,
            resource_name=resource.name if resource else "Resource",
            borrower_id=req.borrower_id,
            borrower_name=borrower_profile.full_name if borrower_profile else "Borrower",
            owner_id=req.owner_id,
            owner_name=owner_profile.full_name if owner_profile else "Owner",
            requested_from=req.requested_from,
            requested_until=req.requested_until,
            message=req.message,
            status=req.status,
            created_at=req.created_at
        ))
    return results

@router.post("/{request_id}/accept")
def accept_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return borrow_service.accept_borrow_request(db, request_id, current_user.user_id)

@router.post("/{request_id}/reject", response_model=BorrowRequestResponse)
def reject_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = borrow_service.reject_borrow_request(db, request_id, current_user.user_id)
    resource = db.query(Resource).filter(Resource.resource_id == req.resource_id).first()
    borrower_profile = db.query(StudentProfile).filter(StudentProfile.user_id == req.borrower_id).first()
    owner_profile = db.query(StudentProfile).filter(StudentProfile.user_id == req.owner_id).first()

    return BorrowRequestResponse(
        request_id=req.request_id,
        resource_id=req.resource_id,
        resource_name=resource.name if resource else "Resource",
        borrower_id=req.borrower_id,
        borrower_name=borrower_profile.full_name if borrower_profile else "Borrower",
        owner_id=req.owner_id,
        owner_name=owner_profile.full_name if owner_profile else "Owner",
        requested_from=req.requested_from,
        requested_until=req.requested_until,
        message=req.message,
        status=req.status,
        created_at=req.created_at
    )

@router.post("/{request_id}/cancel", response_model=BorrowRequestResponse)
def cancel_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = borrow_service.cancel_borrow_request(db, request_id, current_user.user_id)
    resource = db.query(Resource).filter(Resource.resource_id == req.resource_id).first()
    borrower_profile = db.query(StudentProfile).filter(StudentProfile.user_id == req.borrower_id).first()
    owner_profile = db.query(StudentProfile).filter(StudentProfile.user_id == req.owner_id).first()

    return BorrowRequestResponse(
        request_id=req.request_id,
        resource_id=req.resource_id,
        resource_name=resource.name if resource else "Resource",
        borrower_id=req.borrower_id,
        borrower_name=borrower_profile.full_name if borrower_profile else "Borrower",
        owner_id=req.owner_id,
        owner_name=owner_profile.full_name if owner_profile else "Owner",
        requested_from=req.requested_from,
        requested_until=req.requested_until,
        message=req.message,
        status=req.status,
        created_at=req.created_at
    )
