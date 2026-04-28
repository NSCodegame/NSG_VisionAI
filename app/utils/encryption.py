"""Encryption utilities for AES-256-GCM encryption/decryption"""
import base64
import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_aes_gcm(plaintext: str, key_hex: str) -> str:
    """
    Encrypt plaintext using AES-256-GCM.

    Args:
        plaintext: Plain text string to encrypt
        key_hex: 64-character hex string (32 bytes) encryption key

    Returns:
        Base64-encoded string containing nonce + ciphertext + tag

    Raises:
        ValueError: If key is not 64 hex characters
    """
    if len(key_hex) != 64:
        raise ValueError("Encryption key must be 64 hex characters (32 bytes)")

    # Convert hex key to bytes
    key = bytes.fromhex(key_hex)

    # Generate random 12-byte nonce (96 bits, recommended for GCM)
    nonce = os.urandom(12)

    # Create AESGCM cipher
    aesgcm = AESGCM(key)

    # Encrypt plaintext (returns ciphertext + 16-byte authentication tag)
    plaintext_bytes = plaintext.encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)

    # Combine nonce + ciphertext for storage
    encrypted_data = nonce + ciphertext

    # Encode as base64 for storage
    return base64.b64encode(encrypted_data).decode("ascii")


def decrypt_aes_gcm(encrypted_b64: str, key_hex: str) -> str:
    """
    Decrypt AES-256-GCM encrypted data.

    Args:
        encrypted_b64: Base64-encoded string containing nonce + ciphertext + tag
        key_hex: 64-character hex string (32 bytes) encryption key

    Returns:
        Decrypted plaintext string

    Raises:
        ValueError: If key is not 64 hex characters or decryption fails
    """
    if len(key_hex) != 64:
        raise ValueError("Encryption key must be 64 hex characters (32 bytes)")

    # Convert hex key to bytes
    key = bytes.fromhex(key_hex)

    # Decode base64
    encrypted_data = base64.b64decode(encrypted_b64)

    # Extract nonce (first 12 bytes) and ciphertext (remaining bytes)
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]

    # Create AESGCM cipher
    aesgcm = AESGCM(key)

    # Decrypt ciphertext
    try:
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")


def encrypt_rtsp_url(rtsp_url: str, master_key: str) -> str:
    """
    Encrypt RTSP URL using AES-256-GCM.

    Args:
        rtsp_url: Plain RTSP URL
        master_key: Master encryption key (64 hex chars)

    Returns:
        Encrypted URL as base64 string
    """
    return encrypt_aes_gcm(rtsp_url, master_key)


def decrypt_rtsp_url(encrypted_url: str, master_key: str) -> str:
    """
    Decrypt RTSP URL using AES-256-GCM.

    Args:
        encrypted_url: Encrypted URL as base64 string
        master_key: Master encryption key (64 hex chars)

    Returns:
        Decrypted RTSP URL
    """
    return decrypt_aes_gcm(encrypted_url, master_key)


def encrypt_binary_aes_gcm(data: bytes, key_hex: str) -> bytes:
    """
    Encrypt raw binary data using AES-256-GCM.
    
    Args:
        data: Raw bytes to encrypt
        key_hex: 64-character hex string key
        
    Returns:
        Raw bytes (nonce + ciphertext + tag)
    """
    if len(key_hex) != 64:
        raise ValueError("Encryption key must be 64 hex characters (32 bytes)")

    key = bytes.fromhex(key_hex)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    
    # Encrypt (returns ciphertext + 16-byte tag)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    
    return nonce + ciphertext


def decrypt_binary_aes_gcm(encrypted_data: bytes, key_hex: str) -> bytes:
    """
    Decrypt raw binary data using AES-256-GCM.
    
    Args:
        encrypted_data: Raw bytes (nonce + ciphertext + tag)
        key_hex: 64-character hex string key
        
    Returns:
        Decrypted raw bytes
    """
    if len(key_hex) != 64:
        raise ValueError("Encryption key must be 64 hex characters (32 bytes)")

    key = bytes.fromhex(key_hex)
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise ValueError(f"Binary decryption failed: {str(e)}")
