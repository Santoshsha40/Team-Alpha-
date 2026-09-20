from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

# Authentication Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    student_id_number: Optional[str] = None
    department: Optional[str] = None
    campus_id: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    full_name: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    role: str
    status: str
    full_name: Optional[str] = None
    campus_name: Optional[str] = None

    class Config:
        from_attributes = True

class CategoryResponse(BaseModel):
    category_id: str
    name: str

    class Config:
        from_attributes = True

# Resource Schemas
class ResourceCreate(BaseModel):
    name: str
    description: str
    category_id: str
    condition: str  # NEW, LIKE_NEW, GOOD, FAIR, USED
    pickup_location: str
    optional_deposit: float = 0.0
    image_url: Optional[str] = None

class ResourceResponse(BaseModel):
    resource_id: str
    owner_id: str
    owner_name: str
    name: str
    description: str
    category_id: str
    category_name: str
    condition: str
    availability_status: str
    pickup_location: str
    optional_deposit: float
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Borrow Request Schemas
class BorrowRequestCreate(BaseModel):
    resource_id: str
    requested_from: date
    requested_until: date
    message: Optional[str] = None

class BorrowRequestResponse(BaseModel):
    request_id: str
    resource_id: str
    resource_name: str
    borrower_id: str
    borrower_name: str
    owner_id: str
    owner_name: str
    requested_from: date
    requested_until: date
    message: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Loan Schemas
class LoanResponse(BaseModel):
    loan_id: str
    request_id: str
    resource_id: str
    resource_name: str
    borrower_id: str
    borrower_name: str
    owner_id: str
    owner_name: str
    start_date: date
    end_date: date
    status: str
    handover_token: Optional[str] = None

    class Config:
        from_attributes = True

class HandoverVerify(BaseModel):
    handover_token: str

class ReportCreate(BaseModel):
    reported_user_id: Optional[str] = None
    resource_id: Optional[str] = None
    reason: str
    details: str

class ReportResponse(BaseModel):
    report_id: str
    reporter_id: str
    reported_user_id: Optional[str] = None
    resource_id: Optional[str] = None
    reason: str
    details: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
