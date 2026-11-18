from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.schemas.user_schema import UserCreate, UserLogin, Token
from app.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    email_clean = str(user_data.email).strip().lower()
    org_name_clean = user_data.org_name.strip()

    if not org_name_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Organization name cannot be empty."
        )

    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered. Please log in."
        )

    existing_org = db.query(Organization).filter(Organization.name == org_name_clean).first()
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Organization name already taken. Please choose another."
        )

    try:
        # 1. Stage Organization
        new_org = Organization(name=org_name_clean)
        db.add(new_org)
        db.flush() 

        # 2. Stage User with hashed password and tenant reference
        hashed_pw = get_password_hash(user_data.password)
        new_user = User(email=email_clean, hashed_password=hashed_pw, organization_id=new_org.id)
        db.add(new_user)
        
        # 3. ATOMIC COMMIT
        db.commit()
        db.refresh(new_user)
        db.refresh(new_org)
        
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal error occurred during registration. Transaction reverted."
        )

    # 4. Issue Tenant-bound JWT
    access_token = create_access_token(data={"sub": new_user.email, "org_id": new_org.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    email_clean = str(user_data.email).strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email, "org_id": user.organization_id})
    return {"access_token": access_token, "token_type": "bearer"}