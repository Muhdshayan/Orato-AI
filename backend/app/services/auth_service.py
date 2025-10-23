import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.core.database import execute_query
from app.core.config import settings

# Simple password handling (no hashing for now)

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class AuthService:
    """Authentication service for user management and JWT tokens"""
    
    def __init__(self):
        """Initialize the authentication service"""
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    
    def verify_password(self, plain_password: str, stored_password: str) -> bool:
        """Verify a password (simple comparison)"""
        return plain_password == stored_password
    
    def get_password_hash(self, password: str) -> str:
        """Store password as plain text (for simplicity)"""
        return password
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user with email and password"""
        try:
            # Get user from database
            query = """
            SELECT user_id, name, email, password_hash, role, created_at
            FROM users 
            WHERE email = %s
            """
            result = execute_query(query, (email,), fetch_one=True)
            
            if not result:
                return None
            
            # Verify password
            if not self.verify_password(password, result["password_hash"]):
                return None
            
            # Return user data (without password)
            return {
                "user_id": result["user_id"],
                "name": result["name"],
                "email": result["email"],
                "role": result["role"],
                "created_at": result["created_at"]
            }
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return None
    
    def create_user(self, name: str, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Create a new user with hashed password"""
        try:
            # Validate input
            if not name or not email or not password:
                print("❌ Missing required fields")
                return None
            
            # Check password length
            if len(password) < 6:
                print("❌ Password too short")
                return None
            
            # Check if user already exists
            existing_user = execute_query(
                "SELECT user_id FROM users WHERE email = %s",
                (email,),
                fetch_one=True
            )
            
            if existing_user:
                print(f"❌ User already exists with email: {email}")
                return None  # User already exists
            
            # Create new user
            user_id = str(uuid.uuid4())
            password_plain = self.get_password_hash(password)
            
            query = """
            INSERT INTO users (user_id, name, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id, name, email, role, created_at
            """
            
            result = execute_query(
                query,
                (user_id, name, email, password_plain, 'USER'),
                fetch_one=True
            )
            
            print(f"✅ User created successfully: {result['user_id']}")
            return {
                "user_id": result["user_id"],
                "name": result["name"],
                "email": result["email"],
                "role": result["role"],
                "created_at": result["created_at"]
            }
            
        except Exception as e:
            print(f"❌ User creation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            query = """
            SELECT user_id, name, email, role, created_at
            FROM users 
            WHERE user_id = %s
            """
            result = execute_query(query, (user_id,), fetch_one=True)
            
            if result:
                return {
                    "user_id": result["user_id"],
                    "name": result["name"],
                    "email": result["email"],
                    "role": result["role"],
                    "created_at": result["created_at"]
                }
            return None
            
        except Exception as e:
            print(f"❌ Get user error: {e}")
            return None

# Global auth service instance
auth_service = AuthService()
