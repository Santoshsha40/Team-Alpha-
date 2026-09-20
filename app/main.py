from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.models.entities import Campus, Category, User, StudentProfile
from app.core.security import get_password_hash
from app.routers import auth, resources, borrow_requests, loans, reports, admin, notifications

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="CampusLoop — Smart Campus Resource Exchange Production Backend System"
)
@app.get("/")
def root():
    return {
        "message": "CampusLoop API is running",
        "status": "healthy"
    }
# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Seeding Event
@app.on_event("startup")
def startup_db_seed():
    db = SessionLocal()
    try:
        # Seed Default Campus
        campus = db.query(Campus).first()
        if not campus:
            campus = Campus(name="MIT Innovation Campus", domain_suffix="mit.edu")
            db.add(campus)
            db.commit()
            db.refresh(campus)

        # Seed Categories
        categories = ["Electronics", "Academic Books", "Lab Equipment", "Adapters & Chargers", "Sports Gear", "Stationery"]
        for cat_name in categories:
            if not db.query(Category).filter(Category.name == cat_name).first():
                db.add(Category(name=cat_name))
        db.commit()

        # Seed Demo Admin User
        admin_email = "admin@campus.edu"
        if not db.query(User).filter(User.email == admin_email).first():
            admin_user = User(
                campus_id=campus.campus_id,
                email=admin_email,
                password_hash=get_password_hash("Admin123!"),
                role="ADMIN",
                status="ACTIVE"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

            db.add(StudentProfile(
                user_id=admin_user.user_id,
                full_name="Campus Admin Moderator",
                department="Platform Operations"
            ))
            db.commit()

        # Seed Demo Student A (Owner)
        student_a_email = "studenta@campus.edu"
        if not db.query(User).filter(User.email == student_a_email).first():
            st_a = User(
                campus_id=campus.campus_id,
                email=student_a_email,
                password_hash=get_password_hash("Student123!"),
                role="STUDENT",
                status="ACTIVE"
            )
            db.add(st_a)
            db.commit()
            db.refresh(st_a)

            db.add(StudentProfile(
                user_id=st_a.user_id,
                full_name="Sarah Chen",
                student_id_number="STU89123",
                department="Computer Science"
            ))
            db.commit()

        # Seed Demo Student B (Borrower)
        student_b_email = "studentb@campus.edu"
        if not db.query(User).filter(User.email == student_b_email).first():
            st_b = User(
                campus_id=campus.campus_id,
                email=student_b_email,
                password_hash=get_password_hash("Student123!"),
                role="STUDENT",
                status="ACTIVE"
            )
            db.add(st_b)
            db.commit()
            db.refresh(st_b)

            db.add(StudentProfile(
                user_id=st_b.user_id,
                full_name="Alex Rivera",
                student_id_number="STU99410",
                department="Electrical Engineering"
            ))
            db.commit()

    finally:
        db.close()

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(resources.router, prefix=settings.API_V1_STR)
app.include_router(borrow_requests.router, prefix=settings.API_V1_STR)
app.include_router(loans.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "CampusLoop Backend", "version": "1.0.0"}

@app.get("/ready")
def readiness_check():
    return {"status": "ready", "database": "connected"}
