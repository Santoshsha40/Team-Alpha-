import secrets
import time
import base64
import io
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import qrcode
from app.models.entities import Loan, HandoverEvent, AuditLog, Resource
from app.core.security import generate_qr_hmac, verify_qr_hmac

def generate_handover_token(db: Session, loan_id: str, expires_in_minutes: int = 120) -> dict:
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan record not found")
    
    if loan.status not in ["RESERVED", "ACTIVE"]:
        raise HTTPException(status_code=400, detail=f"Cannot generate handover token for loan in state {loan.status}")
    
    nonce = secrets.token_hex(8)
    expires_at_dt = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    expires_at_ts = int(expires_at_dt.timestamp())
    
    signature = generate_qr_hmac(loan_id, nonce, expires_at_ts)
    token_str = f"{loan_id}.{nonce}.{expires_at_ts}.{signature}"

    # Store event record
    event = HandoverEvent(
        loan_id=loan_id,
        token_hash=signature,
        nonce=nonce,
        expires_at=expires_at_dt,
        is_used=False
    )
    db.add(event)
    db.commit()

    # Generate QR Base64 image
    qr_img = qrcode.make(token_str)
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return {
        "loan_id": loan_id,
        "token": token_str,
        "qr_code_url": f"data:image/png;base64,{qr_base64}",
        "expires_at": expires_at_dt.isoformat()
    }

def verify_and_complete_handover(db: Session, handover_token: str, current_user_id: str, expected_loan_id: str = None) -> Loan:
    parts = handover_token.split(".")
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="Invalid QR token format")
    
    loan_id, nonce, expires_at_str, signature = parts
    expires_at_ts = int(expires_at_str)

    if expected_loan_id and loan_id != expected_loan_id:
        raise HTTPException(status_code=400, detail="Handover token does not match target loan ID")

    if time.time() > expires_at_ts:
        raise HTTPException(status_code=400, detail="QR Handover token has expired")

    if not verify_qr_hmac(loan_id, nonce, expires_at_ts, signature):
        raise HTTPException(status_code=400, detail="Invalid cryptographic signature on QR token")

    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status not in ["RESERVED", "ACTIVE"]:
        raise HTTPException(status_code=400, detail=f"Cannot perform handover scan for loan in state '{loan.status}'")

    # Authorize: Must be borrower or owner
    if current_user_id not in [loan.borrower_id, loan.owner_id]:
        raise HTTPException(status_code=403, detail="Not authorized to perform handover scan for this loan")

    event = db.query(HandoverEvent).filter(
        HandoverEvent.loan_id == loan_id,
        HandoverEvent.token_hash == signature
    ).first()

    if not event or event.is_used:
        raise HTTPException(status_code=400, detail="QR token already used or invalid")

    # Update state
    event.is_used = True
    event.verified_at = datetime.now(timezone.utc)
    event.verified_by_role = "BORROWER" if current_user_id == loan.borrower_id else "OWNER"

    loan.status = "HANDED_OVER"

    # Update Resource Availability
    resource = db.query(Resource).filter(Resource.resource_id == loan.resource_id).first()
    if resource:
        resource.availability_status = "ON_LOAN"

    db.commit()
    db.refresh(loan)

    # Log audit event
    audit = AuditLog(
        user_id=current_user_id,
        action="QR_HANDOVER_VERIFIED",
        entity_type="LOAN",
        entity_id=loan_id,
        details=f"Loan status transitioned to HANDED_OVER via QR token"
    )
    db.add(audit)
    db.commit()

    return loan
