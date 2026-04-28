"""Unit tests for Video Feed Service (no database required)"""
import pytest

from app.utils.encryption import decrypt_rtsp_url, encrypt_rtsp_url
from app.core.config import settings


def test_rtsp_url_encryption_round_trip():
    """
    **Validates: Requirements 2.2**
    
    Property 2: RTSP URL Encryption Round-Trip
    
    For any valid RTSP URL string, encrypting the URL using AES-256-GCM
    and then decrypting it SHALL produce a string equivalent to the original URL.
    """
    test_urls = [
        "rtsp://admin:password@192.168.1.100:554/stream1",
        "rtsp://user:pass123@camera.local:8554/live/main",
        "rtsp://10.0.0.50:554/h264",
        "rtsp://admin:p@ssw0rd!@192.168.1.200:554/stream/channel/1",
        "rtsp://camera1.example.com/video",
        "rtsp://192.168.1.1:554/",
        "rtsp://user@host:554/path",
        "rtsp://host/stream",
    ]
    
    for url in test_urls:
        # Encrypt
        encrypted = encrypt_rtsp_url(url, settings.encryption_master_key)
        
        # Verify encrypted is different from original
        assert encrypted != url, f"Encrypted URL should differ from original: {url}"
        assert "rtsp://" not in encrypted, f"Encrypted URL should not contain 'rtsp://': {encrypted}"
        
        # Decrypt
        decrypted = decrypt_rtsp_url(encrypted, settings.encryption_master_key)
        
        # Verify round-trip
        assert decrypted == url, f"Round-trip failed for URL: {url}"


def test_encryption_produces_different_ciphertexts():
    """
    Test that encrypting the same URL multiple times produces different ciphertexts
    (due to random nonce in AES-GCM)
    """
    url = "rtsp://admin:password@192.168.1.100:554/stream"
    
    encrypted1 = encrypt_rtsp_url(url, settings.encryption_master_key)
    encrypted2 = encrypt_rtsp_url(url, settings.encryption_master_key)
    
    # Different ciphertexts (due to random nonce)
    assert encrypted1 != encrypted2
    
    # But both decrypt to same plaintext
    assert decrypt_rtsp_url(encrypted1, settings.encryption_master_key) == url
    assert decrypt_rtsp_url(encrypted2, settings.encryption_master_key) == url


def test_encryption_with_special_characters():
    """Test encryption with URLs containing special characters"""
    special_urls = [
        "rtsp://user:p@ss!w0rd#$%@192.168.1.100:554/stream",
        "rtsp://admin:パスワード@192.168.1.100:554/stream",  # Japanese characters
        "rtsp://user:密码@192.168.1.100:554/stream",  # Chinese characters
        "rtsp://admin:пароль@192.168.1.100:554/stream",  # Cyrillic characters
    ]
    
    for url in special_urls:
        encrypted = encrypt_rtsp_url(url, settings.encryption_master_key)
        decrypted = decrypt_rtsp_url(encrypted, settings.encryption_master_key)
        assert decrypted == url, f"Round-trip failed for URL with special chars: {url}"


def test_decryption_with_wrong_key_fails():
    """Test that decryption with wrong key fails"""
    url = "rtsp://admin:password@192.168.1.100:554/stream"
    encrypted = encrypt_rtsp_url(url, settings.encryption_master_key)
    
    # Try to decrypt with wrong key
    wrong_key = "0" * 64
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_rtsp_url(encrypted, wrong_key)


def test_encryption_with_invalid_key_length():
    """Test that encryption with invalid key length fails"""
    url = "rtsp://admin:password@192.168.1.100:554/stream"
    
    # Too short key
    with pytest.raises(ValueError, match="Encryption key must be 64 hex characters"):
        encrypt_rtsp_url(url, "short_key")
    
    # Too long key
    with pytest.raises(ValueError, match="Encryption key must be 64 hex characters"):
        encrypt_rtsp_url(url, "a" * 128)


def test_decryption_with_invalid_key_length():
    """Test that decryption with invalid key length fails"""
    encrypted = "some_encrypted_data"
    
    # Too short key
    with pytest.raises(ValueError, match="Encryption key must be 64 hex characters"):
        decrypt_rtsp_url(encrypted, "short_key")


def test_decryption_with_invalid_base64():
    """Test that decryption with invalid base64 data fails"""
    invalid_encrypted = "not_valid_base64!!!"
    
    with pytest.raises(Exception):  # Will raise base64 decode error or decryption error
        decrypt_rtsp_url(invalid_encrypted, settings.encryption_master_key)


def test_rtsp_url_validation():
    """Test RTSP URL format validation"""
    from app.services.feed_service import FeedService
    from unittest.mock import MagicMock
    
    # Create service with mock session
    mock_session = MagicMock()
    service = FeedService(mock_session)
    
    # Valid RTSP URLs
    valid_urls = [
        "rtsp://192.168.1.100:554/stream",
        "rtsp://admin:pass@192.168.1.100:554/stream",
        "rtsp://camera.local/stream",
        "rtsp://10.0.0.1:8554/live/main",
        "RTSP://HOST/PATH",  # Case insensitive
    ]
    
    for url in valid_urls:
        assert service._validate_rtsp_url(url), f"Should be valid: {url}"
    
    # Invalid URLs
    invalid_urls = [
        "http://192.168.1.100/stream",  # Wrong protocol
        "https://192.168.1.100/stream",  # Wrong protocol
        "ftp://192.168.1.100/stream",  # Wrong protocol
        "192.168.1.100:554/stream",  # Missing protocol
        "rtsp//192.168.1.100/stream",  # Missing colon
    ]
    
    for url in invalid_urls:
        assert not service._validate_rtsp_url(url), f"Should be invalid: {url}"
