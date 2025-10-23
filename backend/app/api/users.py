from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.services.auth_service import auth_service
from datetime import timedelta

router = APIRouter()
security = HTTPBearer()

# Request/Response Models
class UserSignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=6, max_length=100, description="Password")

class UserSigninRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    created_at: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[str] = None

# Dependency to get current user from token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = auth_service.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

@router.post("/signup", response_model=AuthResponse)
async def signup(user_data: UserSignupRequest):
    """Sign up a new user"""
    try:
        # Create user
        user = auth_service.create_user(
            name=user_data.name,
            email=user_data.email,
            password=user_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = auth_service.create_access_token(
            data={"sub": user["user_id"]}, 
            expires_delta=access_token_expires
        )
        
        print(f"✅ User signed up successfully: {user['user_id']}")
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                user_id=user["user_id"],
                name=user["name"],
                email=user["email"],
                role=user["role"],
                created_at=user["created_at"].isoformat()
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Signup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )

@router.post("/signin", response_model=AuthResponse)
async def signin(user_data: UserSigninRequest):
    """Sign in an existing user"""
    try:
        # Authenticate user
        user = auth_service.authenticate_user(user_data.email, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = auth_service.create_access_token(
            data={"sub": user["user_id"]}, 
            expires_delta=access_token_expires
        )
        
        print(f"✅ User signed in successfully: {user['user_id']}")
        
        return AuthResponse(
            access_token=access_token,
            user=UserResponse(
                user_id=user["user_id"],
                name=user["name"],
                email=user["email"],
                role=user["role"],
                created_at=user["created_at"].isoformat()
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Signin error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to authenticate user: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        user_id=current_user["user_id"],
        name=current_user["name"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=current_user["created_at"].isoformat()
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID (public endpoint)"""
    try:
        user = auth_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return UserResponse(
            user_id=user["user_id"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user: {str(e)}"
        )
