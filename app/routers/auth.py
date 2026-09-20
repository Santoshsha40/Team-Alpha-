from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import UserRegister, UserLogin, Token, UserResponse
from app.services import auth_service
from app.routers.dependencies import get_current_user
from app.models.entities import User, StudentProfile, Campus

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, user_data)
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.user_id).first()
    campus = db.query(Campus).filter(Campus.campus_id == user.campus_id).first()
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        status=user.status,
        full_name=profile.full_name if profile else "",
        campus_name=campus.name if campus else ""
    )

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    return auth_service.authenticate_user(db, login_data)

@router.post("/refresh", response_model=Token)
def refresh(payload: dict, db: Session = Depends(get_db)):
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token is required")
    return auth_service.refresh_user_token(db, refresh_token)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.user_id).first()
    campus = db.query(Campus).filter(Campus.campus_id == current_user.campus_id).first()
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
        full_name=profile.full_name if profile else "",
        campus_name=campus.name if campus else ""
    )
