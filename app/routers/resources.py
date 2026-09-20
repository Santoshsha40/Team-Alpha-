from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.schemas import ResourceCreate, ResourceResponse, CategoryResponse
from app.models.entities import Resource, User, Category, StudentProfile
from app.routers.dependencies import get_current_user
from app.services.availability_service import is_resource_available

router = APIRouter(prefix="/resources", tags=["Resources"])

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.get("", response_model=List[ResourceResponse])
def search_resources(
    q: Optional[str] = Query(None, description="Search keyword"),
    category_id: Optional[str] = Query(None, description="Category UUID filter"),
    condition: Optional[str] = Query(None, description="Condition filter"),
    available_from: Optional[date] = Query(None, description="Start date for availability filter"),
    available_until: Optional[date] = Query(None, description="End date for availability filter"),
    db: Session = Depends(get_db)
):
    query = db.query(Resource).filter(Resource.deleted_at.is_(None))

    if q:
        search_pattern = f"%{q}%"
        query = query.filter((Resource.name.ilike(search_pattern)) | (Resource.description.ilike(search_pattern)))

    if category_id:
        query = query.filter(Resource.category_id == category_id)

    if condition:
        query = query.filter(Resource.condition == condition)

    resources = query.all()
    results = []

    for res in resources:
        # Check date range availability if provided
        if available_from and available_until:
            if not is_resource_available(db, res.resource_id, available_from, available_until):
                continue

        owner = db.query(User).filter(User.user_id == res.owner_id).first()
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == res.owner_id).first() if owner else None
        category = db.query(Category).filter(Category.category_id == res.category_id).first()

        results.append(ResourceResponse(
            resource_id=res.resource_id,
            owner_id=res.owner_id,
            owner_name=profile.full_name if profile else "Student Owner",
            name=res.name,
            description=res.description,
            category_id=res.category_id,
            category_name=category.name if category else "General",
            condition=res.condition,
            availability_status=res.availability_status,
            pickup_location=res.pickup_location,
            optional_deposit=res.optional_deposit,
            image_url=res.image_url,
            created_at=res.created_at
        ))

    return results

from datetime import datetime

@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(
    res_data: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_res = Resource(
        owner_id=current_user.user_id,
        category_id=res_data.category_id,
        campus_id=current_user.campus_id,
        name=res_data.name,
        description=res_data.description,
        condition=res_data.condition,
        pickup_location=res_data.pickup_location,
        optional_deposit=res_data.optional_deposit,
        image_url=res_data.image_url
    )
    db.add(new_res)
    db.commit()
    db.refresh(new_res)

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.user_id).first()
    category = db.query(Category).filter(Category.category_id == res_data.category_id).first()

    return ResourceResponse(
        resource_id=new_res.resource_id,
        owner_id=new_res.owner_id,
        owner_name=profile.full_name if profile else "Student Owner",
        name=new_res.name,
        description=new_res.description,
        category_id=new_res.category_id,
        category_name=category.name if category else "General",
        condition=new_res.condition,
        availability_status=new_res.availability_status,
        pickup_location=new_res.pickup_location,
        optional_deposit=new_res.optional_deposit,
        image_url=new_res.image_url,
        created_at=new_res.created_at
    )

@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: str, db: Session = Depends(get_db)):
    res = db.query(Resource).filter(Resource.resource_id == resource_id, Resource.deleted_at.is_(None)).first()
    if not res:
        raise HTTPException(status_code=404, detail="Resource not found")

    owner_profile = db.query(StudentProfile).filter(StudentProfile.user_id == res.owner_id).first()
    category = db.query(Category).filter(Category.category_id == res.category_id).first()

    return ResourceResponse(
        resource_id=res.resource_id,
        owner_id=res.owner_id,
        owner_name=owner_profile.full_name if owner_profile else "Student Owner",
        name=res.name,
        description=res.description,
        category_id=res.category_id,
        category_name=category.name if category else "General",
        condition=res.condition,
        availability_status=res.availability_status,
        pickup_location=res.pickup_location,
        optional_deposit=res.optional_deposit,
        image_url=res.image_url,
        created_at=res.created_at
    )

@router.put("/{resource_id}", response_model=ResourceResponse)
def update_resource(
    resource_id: str,
    res_data: ResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    res = db.query(Resource).filter(Resource.resource_id == resource_id, Resource.deleted_at.is_(None)).first()
    if not res:
        raise HTTPException(status_code=404, detail="Resource not found")

    if res.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only owner can update this resource")

    res.name = res_data.name
    res.description = res_data.description
    res.category_id = res_data.category_id
    res.condition = res_data.condition
    res.pickup_location = res_data.pickup_location
    res.optional_deposit = res_data.optional_deposit
    if res_data.image_url is not None:
        res.image_url = res_data.image_url

    db.commit()
    db.refresh(res)

    owner_profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.user_id).first()
    category = db.query(Category).filter(Category.category_id == res.category_id).first()

    return ResourceResponse(
        resource_id=res.resource_id,
        owner_id=res.owner_id,
        owner_name=owner_profile.full_name if owner_profile else "Student Owner",
        name=res.name,
        description=res.description,
        category_id=res.category_id,
        category_name=category.name if category else "General",
        condition=res.condition,
        availability_status=res.availability_status,
        pickup_location=res.pickup_location,
        optional_deposit=res.optional_deposit,
        image_url=res.image_url,
        created_at=res.created_at
    )

@router.delete("/{resource_id}")
def delete_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    res = db.query(Resource).filter(Resource.resource_id == resource_id, Resource.deleted_at.is_(None)).first()
    if not res:
        raise HTTPException(status_code=404, detail="Resource not found")

    if res.owner_id != current_user.user_id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to delete this resource")

    res.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": f"Resource '{res.name}' deleted successfully"}
