"""
Encryption Manager for sensitive data protection
"""

import base64
import hashlib
import secrets
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json
import logging

logger = logging.getLogger(__name__)

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = self._generate_master_key()
        
        self.fernet = self._create_fernet_instance()
    
    def _generate_master_key(self) -> bytes:
        """Generate a new master key"""
        return secrets.token_bytes(32)
    
    def _create_fernet_instance(self) -> Fernet:
        """Create Fernet instance from master key"""
        # Derive key using PBKDF2
        salt = b'npcl_voice_assistant_salt'  # In production, use random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    async def encrypt(self, data: Any) -> str:
        """Encrypt data and return base64 encoded string"""
        try:
            # Convert data to JSON string
            if isinstance(data, (dict, list)):
                json_data = json.dumps(data)
            else:
                json_data = str(data)
            
            # Encrypt data
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            # Return base64 encoded string
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    async def decrypt(self, encrypted_data: str) -> Any:
        """Decrypt base64 encoded string and return original data"""
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            
            # Decrypt data
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            
            # Convert back to original format
            json_str = decrypted_data.decode()
            
            try:
                # Try to parse as JSON
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Return as string if not JSON
                return json_str
                
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # Use PBKDF2 for password hashing
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        password_hash = kdf.derive(password.encode())
        
        return {
            'hash': base64.b64encode(password_hash).decode(),
            'salt': base64.b64encode(salt).decode()
        }
    
    def verify_password(self, password: str, stored_hash: str, stored_salt: str) -> bool:
        """Verify password against stored hash"""
        try:
            salt = base64.b64decode(stored_salt.encode())
            expected_hash = base64.b64decode(stored_hash.encode())
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            password_hash = kdf.derive(password.encode())
            return password_hash == expected_hash
            
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    def hash_data(self, data: str) -> str:
        """Create SHA-256 hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()