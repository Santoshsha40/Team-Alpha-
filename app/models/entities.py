import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, Numeric, Date, DateTime, ForeignKey, Float, Enum, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Campus(Base):
    __tablename__ = "campuses"

    campus_id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    domain_suffix = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="campus")
    resources = relationship("Resource", back_populates="campus")


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=generate_uuid)
    campus_id = Column(String(36), ForeignKey("campuses.campus_id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="STUDENT")  # STUDENT, ADMIN
    status = Column(String(20), default="ACTIVE") # ACTIVE, SUSPENDED
    created_at = Column(DateTime, default=datetime.utcnow)

    campus = relationship("Campus", back_populates="users")
    profile = relationship("StudentProfile", back_populates="user", uselist=False)
    resources = relationship("Resource", back_populates="owner")
    borrow_requests = relationship("BorrowRequest", foreign_keys="BorrowRequest.borrower_id", back_populates="borrower")
    loans_as_borrower = relationship("Loan", foreign_keys="Loan.borrower_id", back_populates="borrower")
    loans_as_owner = relationship("Loan", foreign_keys="Loan.owner_id", back_populates="owner")
    notifications = relationship("Notification", back_populates="user")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    profile_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.user_id"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    student_id_number = Column(String(100), nullable=True)
    department = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    rating_score = Column(Float, default=5.0)

    user = relationship("User", back_populates="profile")


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    icon = Column(String(50), nullable=True)

    resources = relationship("Resource", back_populates="category")


class Resource(Base):
    __tablename__ = "resources"

    resource_id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.category_id"), nullable=False)
    campus_id = Column(String(36), ForeignKey("campuses.campus_id"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    condition = Column(String(20), nullable=False) # NEW, LIKE_NEW, GOOD, FAIR, USED
    availability_status = Column(String(20), default="AVAILABLE") # AVAILABLE, RESERVED, ON_LOAN, MAINTENANCE
    image_url = Column(String(500), nullable=True)
    pickup_location = Column(String(255), nullable=False)
    optional_deposit = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="resources")
    category = relationship("Category", back_populates="resources")
    campus = relationship("Campus", back_populates="resources")
    borrow_requests = relationship("BorrowRequest", back_populates="resource")
    loans = relationship("Loan", back_populates="resource")


class BorrowRequest(Base):
    __tablename__ = "borrow_requests"

    request_id = Column(String(36), primary_key=True, default=generate_uuid)
    resource_id = Column(String(36), ForeignKey("resources.resource_id"), nullable=False)
    borrower_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    owner_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    requested_from = Column(Date, nullable=False)
    requested_until = Column(Date, nullable=False)
    message = Column(Text, nullable=True)
    status = Column(String(20), default="PENDING") # PENDING, ACCEPTED, REJECTED, CANCELLED, EXPIRED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resource = relationship("Resource", back_populates="borrow_requests")
    borrower = relationship("User", foreign_keys=[borrower_id], back_populates="borrow_requests")
    loan = relationship("Loan", back_populates="request", uselist=False)


class Loan(Base):
    __tablename__ = "loans"

    loan_id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(36), ForeignKey("borrow_requests.request_id"), unique=True, nullable=False)
    resource_id = Column(String(36), ForeignKey("resources.resource_id"), nullable=False)
    borrower_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    owner_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(30), default="RESERVED") # RESERVED, HANDED_OVER, ACTIVE, RETURN_REQUESTED, RETURNED, OVERDUE, DISPUTED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("BorrowRequest", back_populates="loan")
    resource = relationship("Resource", back_populates="loans")
    borrower = relationship("User", foreign_keys=[borrower_id], back_populates="loans_as_borrower")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="loans_as_owner")
    handover_events = relationship("HandoverEvent", back_populates="loan")


class HandoverEvent(Base):
    __tablename__ = "handover_events"

    handover_id = Column(String(36), primary_key=True, default=generate_uuid)
    loan_id = Column(String(36), ForeignKey("loans.loan_id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    nonce = Column(String(100), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    loan = relationship("Loan", back_populates="handover_events")


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(String(36), primary_key=True, default=generate_uuid)
    reporter_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    reported_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=True)
    resource_id = Column(String(36), ForeignKey("resources.resource_id"), nullable=True)
    reason = Column(String(100), nullable=False)
    details = Column(Text, nullable=False)
    status = Column(String(20), default="OPEN") # OPEN, UNDER_REVIEW, RESOLVED, REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
