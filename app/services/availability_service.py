from datetime import date
from sqlalchemy.orm import Session
from app.models.entities import Loan

def parse_to_date(val):
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        return date.fromisoformat(val)
    return date.fromisoformat(str(val))

def is_resource_available(db: Session, resource_id: str, requested_from: date, requested_until: date) -> bool:
    """
    Checks if a resource is available for the given date range.
    A conflict occurs if an existing active loan/reservation overlaps:
    (start_date <= requested_until) AND (end_date >= requested_from)
    """
    req_from = parse_to_date(requested_from)
    req_until = parse_to_date(requested_until)

    if req_until < req_from:
        return False

    active_loans = db.query(Loan).filter(
        Loan.resource_id == resource_id,
        Loan.status.in_(["RESERVED", "HANDED_OVER", "ACTIVE", "RETURN_REQUESTED"])
    ).all()

    for loan in active_loans:
        start_d = parse_to_date(loan.start_date)
        end_d = parse_to_date(loan.end_date)

        # Overlap condition: start <= req_until AND end >= req_from
        if start_d <= req_until and end_d >= req_from:
            return False

    return True
