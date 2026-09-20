import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, close_all_sessions
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_db
from app.models.entities import Category, Campus

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_campusloop_nullpool.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=NullPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.rollback()
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    close_all_sessions()
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed campus and categories cleanly
    db = TestingSessionLocal()
    try:
        campus = Campus(name="MIT Innovation Campus", domain_suffix="mit.edu")
        db.add(campus)
        db.commit()

        categories = ["Electronics", "Academic Books", "Lab Equipment", "Adapters & Chargers", "Sports Gear", "Stationery"]
        for cat_name in categories:
            db.add(Category(name=cat_name))
        db.commit()
    finally:
        db.close()

    yield
    close_all_sessions()
    engine.dispose()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_user_registration_and_login(client):
    reg_payload = {
        "email": "teststudent@campus.edu",
        "password": "Password123!",
        "full_name": "Test Student"
    }
    response = client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "teststudent@campus.edu"

    # Login
    login_payload = {
        "email": "teststudent@campus.edu",
        "password": "Password123!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data

def test_borrow_request_lifecycle_and_qr(client):
    # 1. Register Owner
    client.post("/api/v1/auth/register", json={"email": "owner@campus.edu", "password": "Password123!", "full_name": "Owner User"})
    owner_login = client.post("/api/v1/auth/login", json={"email": "owner@campus.edu", "password": "Password123!"}).json()
    owner_token = owner_login["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Register Borrower
    client.post("/api/v1/auth/register", json={"email": "borrower@campus.edu", "password": "Password123!", "full_name": "Borrower User"})
    borrower_login = client.post("/api/v1/auth/login", json={"email": "borrower@campus.edu", "password": "Password123!"}).json()
    borrower_token = borrower_login["access_token"]
    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}

    # Fetch Category ID via API
    categories = client.get("/api/v1/resources/categories").json()
    cat_id = categories[0]["category_id"]

    # 3. Create Resource
    res_payload = {
        "name": "Scientific Calculator TI-84 Plus",
        "description": "Graphing calculator for stats",
        "category_id": cat_id,
        "condition": "GOOD",
        "pickup_location": "Library Desk 1",
        "optional_deposit": 10.00
    }
    create_res = client.post("/api/v1/resources", json=res_payload, headers=owner_headers)
    assert create_res.status_code == 201
    resource_id = create_res.json()["resource_id"]

    # 4. Borrower Requests Resource
    today = date.today()
    from_date = (today + timedelta(days=1)).isoformat()
    until_date = (today + timedelta(days=4)).isoformat()

    req_payload = {
        "resource_id": resource_id,
        "requested_from": from_date,
        "requested_until": until_date,
        "message": "Physics exam practice"
    }
    req_res = client.post("/api/v1/borrow-requests", json=req_payload, headers=borrower_headers)
    assert req_res.status_code == 201
    request_id = req_res.json()["request_id"]

    # 5. Owner Accepts Request -> Loan & QR Generated
    accept_res = client.post(f"/api/v1/borrow-requests/{request_id}/accept", headers=owner_headers)
    assert accept_res.status_code == 200
    accept_data = accept_res.json()
    loan_id = accept_data["loan"]["loan_id"]
    handover_token = accept_data["loan"]["handover_token"]
    assert handover_token is not None

    # 6. Verify QR Handover -> Loan becomes ACTIVE/HANDED_OVER
    verify_res = client.post(f"/api/v1/loans/{loan_id}/handover/verify", json={"handover_token": handover_token}, headers=borrower_headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "HANDED_OVER"

    # 7. Borrower Requests Return
    ret_req = client.post(f"/api/v1/loans/{loan_id}/return/request", headers=borrower_headers)
    assert ret_req.status_code == 200

    # 8. Owner Confirms Return
    ret_conf = client.post(f"/api/v1/loans/{loan_id}/return/confirm", headers=owner_headers)
    assert ret_conf.status_code == 200
    assert ret_conf.json()["status"] == "RETURNED"

def test_double_booking_prevention(client):
    # Fetch Category ID via API
    categories = client.get("/api/v1/resources/categories").json()
    cat_id = categories[0]["category_id"]

    # Register owner & 2 borrowers
    client.post("/api/v1/auth/register", json={"email": "owner2@campus.edu", "password": "Password123!", "full_name": "Owner 2"})
    owner_token = client.post("/api/v1/auth/login", json={"email": "owner2@campus.edu", "password": "Password123!"}).json()["access_token"]
    
    client.post("/api/v1/auth/register", json={"email": "borrowerA@campus.edu", "password": "Password123!", "full_name": "Borrower A"})
    bA_token = client.post("/api/v1/auth/login", json={"email": "borrowerA@campus.edu", "password": "Password123!"}).json()["access_token"]

    client.post("/api/v1/auth/register", json={"email": "borrowerB@campus.edu", "password": "Password123!", "full_name": "Borrower B"})
    bB_token = client.post("/api/v1/auth/login", json={"email": "borrowerB@campus.edu", "password": "Password123!"}).json()["access_token"]

    create_res = client.post("/api/v1/resources", json={
        "name": "Organic Chemistry Textbook",
        "description": "Standard 4th edition",
        "category_id": cat_id,
        "condition": "GOOD",
        "pickup_location": "Library Desk 2"
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert create_res.status_code == 201
    res_id = create_res.json()["resource_id"]

    today = date.today()
    d1 = (today + timedelta(days=5)).isoformat()
    d2 = (today + timedelta(days=10)).isoformat()

    # Borrower A requests & owner accepts
    reqA = client.post("/api/v1/borrow-requests", json={
        "resource_id": res_id, "requested_from": d1, "requested_until": d2
    }, headers={"Authorization": f"Bearer {bA_token}"}).json()

    accept_res = client.post(f"/api/v1/borrow-requests/{reqA['request_id']}/accept", headers={"Authorization": f"Bearer {owner_token}"})
    assert accept_res.status_code == 200

    # Borrower B attempts to request overlapping dates -> should be rejected
    d_overlap_start = (today + timedelta(days=7)).isoformat()
    d_overlap_end = (today + timedelta(days=12)).isoformat()

    reqB_res = client.post("/api/v1/borrow-requests", json={
        "resource_id": res_id, "requested_from": d_overlap_start, "requested_until": d_overlap_end
    }, headers={"Authorization": f"Bearer {bB_token}"})

    assert reqB_res.status_code == 400
    assert "Overlapping reservation exists" in reqB_res.json()["detail"]
