"""
Authentication and Authorization Manager
Handles JWT tokens, API keys, and user authentication
"""

import jwt
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
import bcrypt
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

@dataclass
class User:
    """User model for authentication"""
    user_id: str
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    is_active: bool = True
    created_at: datetime = None
    last_login: datetime = None

@dataclass
class AuthToken:
    """Authentication token model"""
    token: str
    user_id: str
    expires_at: datetime
    token_type: str = "access"
    scopes: List[str] = None

class AuthManager(ABC):
    """Abstract base class for authentication managers"""
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate user with credentials"""
        pass
    
    @abstractmethod
    async def authorize(self, user: User, resource: str, action: str) -> bool:
        """Check if user is authorized for action on resource"""
        pass
    
    @abstractmethod
    async def generate_token(self, user: User) -> AuthToken:
        """Generate authentication token for user"""
        pass
    
    @abstractmethod
    async def validate_token(self, token: str) -> Optional[User]:
        """Validate token and return user"""
        pass

class JWTAuthManager(AuthManager):
    """JWT-based authentication manager"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", 
                 token_expiry: int = 3600):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry = token_expiry
        self.users_db: Dict[str, User] = {}
        self.api_keys: Dict[str, str] = {}  # api_key -> user_id
        self.revoked_tokens: set = set()
        
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate user with various credential types"""
        try:
            auth_type = credentials.get("type", "password")
            
            if auth_type == "password":
                return await self._authenticate_password(credentials)
            elif auth_type == "api_key":
                return await self._authenticate_api_key(credentials)
            elif auth_type == "token":
                return await self._authenticate_token(credentials)
            else:
                logger.warning(f"Unknown authentication type: {auth_type}")
                return None
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def _authenticate_password(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate with username/password"""
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            return None
            
        # In production, this would query a database
        user = self.users_db.get(username)
        if not user or not user.is_active:
            return None
            
        # Verify password (in production, use bcrypt)
        stored_password = credentials.get("stored_password_hash")
        if stored_password and bcrypt.checkpw(password.encode(), stored_password):
            user.last_login = datetime.utcnow()
            return user
            
        return None
    
    async def _authenticate_api_key(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate with API key"""
        api_key = credentials.get("api_key")
        if not api_key:
            return None
            
        user_id = self.api_keys.get(api_key)
        if not user_id:
            return None
            
        # Find user by ID
        for user in self.users_db.values():
            if user.user_id == user_id and user.is_active:
                return user
                
        return None
    
    async def _authenticate_token(self, credentials: Dict[str, Any]) -> Optional[User]:
        """Authenticate with JWT token"""
        token = credentials.get("token")
        return await self.validate_token(token)
    
    async def authorize(self, user: User, resource: str, action: str) -> bool:
        """Check if user is authorized for action on resource"""
        if not user or not user.is_active:
            return False
            
        # Check if user has admin role
        if "admin" in user.roles:
            return True
            
        # Check specific permissions
        required_permission = f"{resource}:{action}"
        if required_permission in user.permissions:
            return True
            
        # Check role-based permissions
        role_permissions = {
            "operator": ["calls:read", "calls:create", "sessions:read"],
            "supervisor": ["calls:*", "sessions:*", "users:read"],
            "admin": ["*:*"]
        }
        
        for role in user.roles:
            permissions = role_permissions.get(role, [])
            if required_permission in permissions or "*:*" in permissions:
                return True
                
        return False
    
    async def generate_token(self, user: User) -> AuthToken:
        """Generate JWT token for user"""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.token_expiry)
        
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "roles": user.roles,
            "permissions": user.permissions,
            "iat": now.timestamp(),
            "exp": expires_at.timestamp(),
            "jti": secrets.token_hex(16)  # JWT ID for revocation
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return AuthToken(
            token=token,
            user_id=user.user_id,
            expires_at=expires_at,
            token_type="access",
            scopes=user.permissions
        )
    
    async def validate_token(self, token: str) -> Optional[User]:
        """Validate JWT token and return user"""
        try:
            if token in self.revoked_tokens:
                return None
                
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None
                
            user_id = payload.get("user_id")
            if not user_id:
                return None
                
            # Find user
            for user in self.users_db.values():
                if user.user_id == user_id and user.is_active:
                    return user
                    
            return None
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get("jti")
            if jti:
                self.revoked_tokens.add(jti)
                return True
        except:
            pass
        return False
    
    async def create_user(self, username: str, email: str, password: str, 
                         roles: List[str] = None) -> User:
        """Create a new user"""
        user_id = secrets.token_hex(16)
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            roles=roles or ["user"],
            permissions=self._get_permissions_for_roles(roles or ["user"]),
            created_at=datetime.utcnow()
        )
        
        self.users_db[username] = user
        return user
    
    async def create_api_key(self, user_id: str) -> str:
        """Create API key for user"""
        api_key = f"npcl_{secrets.token_urlsafe(32)}"
        self.api_keys[api_key] = user_id
        return api_key
    
    def _get_permissions_for_roles(self, roles: List[str]) -> List[str]:
        """Get permissions for given roles"""
        role_permissions = {
            "user": ["calls:read", "sessions:read"],
            "operator": ["calls:read", "calls:create", "sessions:read", "sessions:create"],
            "supervisor": ["calls:*", "sessions:*", "users:read"],
            "admin": ["*:*"]
        }
        
        permissions = set()
        for role in roles:
            permissions.update(role_permissions.get(role, []))
        
        return list(permissions)

class APIKeyManager:
    """Manages API keys for service-to-service authentication"""
    
    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
    
    def generate_api_key(self, service_name: str, permissions: List[str] = None) -> str:
        """Generate API key for service"""
        api_key = f"npcl_service_{secrets.token_urlsafe(32)}"
        
        self.api_keys[api_key] = {
            "service_name": service_name,
            "permissions": permissions or [],
            "created_at": datetime.utcnow(),
            "last_used": None,
            "is_active": True
        }
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return service info"""
        key_info = self.api_keys.get(api_key)
        if key_info and key_info["is_active"]:
            key_info["last_used"] = datetime.utcnow()
            return key_info
        return None
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["is_active"] = False
            return True
        return False