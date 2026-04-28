"""Security utilities for password hashing and JWT tokens"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context with bcrypt (12 rounds as per requirements)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.password_bcrypt_rounds,
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with 12 rounds.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token using RS256 algorithm.

    Args:
        subject: Token subject (typically user ID)
        additional_claims: Additional claims to include in token
        expires_delta: Token expiration time delta (default: 8 hours)

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.jwt_access_token_expire_hours)

    expire = datetime.utcnow() + expires_delta

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    # Load private key for signing
    private_key = settings.jwt_private_key
    if not private_key:
        raise ValueError("JWT private key not configured")

    encoded_jwt = jwt.encode(
        to_encode,
        private_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def create_refresh_token(
    subject: str,
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT refresh token using RS256 algorithm.

    Args:
        subject: Token subject (typically user ID)
        additional_claims: Additional claims to include in token
        expires_delta: Token expiration time delta (default: 30 days)

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)

    expire = datetime.utcnow() + expires_delta

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    # Load private key for signing
    private_key = settings.jwt_private_key
    if not private_key:
        raise ValueError("JWT private key not configured")

    encoded_jwt = jwt.encode(
        to_encode,
        private_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token using RS256 algorithm.

    Args:
        token: Encoded JWT token string

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    # Load public key for verification
    public_key = settings.jwt_public_key
    if not public_key:
        raise ValueError("JWT public key not configured")

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Token validation failed: {str(e)}")


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    """
    Verify token type matches expected type.

    Args:
        payload: Decoded token payload
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        True if token type matches, False otherwise
    """
    token_type = payload.get("type")
    return token_type == expected_type
