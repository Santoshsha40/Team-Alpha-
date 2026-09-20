from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from jose import jwt, JWTError
from app.core.config import settings
from app.models.entities import User, StudentProfile, Campus
from app.schemas.schemas import UserRegister, UserLogin, Token
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token

def register_user(db: Session, user_data: UserRegister) -> User:
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Get or create default campus
    campus = None
    if user_data.campus_id:
        campus = db.query(Campus).filter(Campus.campus_id == user_data.campus_id).first()
    
    if not campus:
        email_domain = user_data.email.split("@")[-1] if "@" in user_data.email else ""
        campus = db.query(Campus).filter(Campus.domain_suffix == email_domain).first()
        if not campus:
            campus = db.query(Campus).first()
            if not campus:
                campus = Campus(name="Main Tech Campus", domain_suffix="campus.edu")
                db.add(campus)
                db.commit()
                db.refresh(campus)

    new_user = User(
        campus_id=campus.campus_id,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role="STUDENT",
        status="ACTIVE"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    profile = StudentProfile(
        user_id=new_user.user_id,
        full_name=user_data.full_name,
        student_id_number=user_data.student_id_number,
        department=user_data.department
    )
    db.add(profile)
    db.commit()

    return new_user

def authenticate_user(db: Session, login_data: UserLogin) -> Token:
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if user.status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended by campus administration"
        )
    
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.user_id).first()
    full_name = profile.full_name if profile else user.email

    access_token = create_access_token(subject=user.user_id)
    refresh_token = create_refresh_token(subject=user.user_id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.user_id,
        role=user.role,
        full_name=full_name
    )

def refresh_user_token(db: Session, refresh_token: str) -> Token:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or user.status == "SUSPENDED":
        raise credentials_exception

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.user_id).first()
    full_name = profile.full_name if profile else user.email

    new_access_token = create_access_token(subject=user.user_id)
    new_refresh_token = create_refresh_token(subject=user.user_id)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user_id=user.user_id,
        role=user.role,
        full_name=full_name
    )
