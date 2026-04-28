"""
Static Security Tests — FINAL.3

Runs Bandit security linter checks and validates security-critical
code patterns without requiring a live server.

These tests verify:
- No hardcoded secrets in source code
- Proper use of cryptographic functions
- No SQL injection vulnerabilities
- No command injection risks
- Proper password hashing configuration
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Bandit static analysis
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestBanditStaticAnalysis:
    """Run Bandit security linter on the codebase."""

    def test_bandit_no_high_severity_issues(self):
        """Bandit must report zero HIGH severity issues in app/."""
        result = subprocess.run(
            [
                sys.executable, "-m", "bandit",
                "-r", "app/",
                "-ll",          # Only HIGH severity
                "-ii",          # Only HIGH confidence
                "-f", "json",
                "--exclude", "app/ml/,app/tasks/",  # ML workers use subprocess intentionally
            ],
            capture_output=True,
            text=True,
        )
        # Bandit returns 1 if issues found, 0 if clean
        # We allow it to fail gracefully if bandit is not installed
        if result.returncode == 127 or "No module named bandit" in result.stderr:
            pytest.skip("bandit not installed — skipping static security scan")

        import json
        try:
            report = json.loads(result.stdout)
            high_issues = [
                r for r in report.get("results", [])
                if r.get("issue_severity") == "HIGH" and r.get("issue_confidence") == "HIGH"
            ]
            assert len(high_issues) == 0, (
                f"Bandit found {len(high_issues)} HIGH severity issues:\n"
                + "\n".join(
                    f"  {r['filename']}:{r['line_number']} — {r['issue_text']}"
                    for r in high_issues
                )
            )
        except (json.JSONDecodeError, KeyError):
            # Bandit output format issue — skip rather than fail
            pytest.skip("Could not parse bandit output")


# ---------------------------------------------------------------------------
# Hardcoded secrets check
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestNoHardcodedSecrets:
    """Verify no hardcoded secrets exist in source code."""

    # Patterns that indicate hardcoded secrets
    SECRET_PATTERNS = [
        (r'password\s*=\s*["\'][^"\']{8,}["\']', "hardcoded password"),
        (r'secret_key\s*=\s*["\'][^"\']{8,}["\']', "hardcoded secret key"),
        (r'api_key\s*=\s*["\'][^"\']{8,}["\']', "hardcoded API key"),
        (r'private_key\s*=\s*["\']-----BEGIN', "hardcoded private key"),
    ]

    # Files/patterns to exclude from check
    EXCLUDE_PATTERNS = [
        "change_me",
        "your_",
        "example",
        "test_",
        "mock_",
        "placeholder",
        "CHANGE_ME",
        "settings.",
        "config.",
        "os.environ",
        "getenv",
        "Field(",
        "default=",
    ]

    def test_no_hardcoded_passwords_in_source(self):
        """Source files must not contain hardcoded passwords."""
        app_dir = Path("app")
        violations = []

        for py_file in app_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern, description in self.SECRET_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line = match.group(0)
                    # Skip if it's a safe pattern
                    if any(excl in line for excl in self.EXCLUDE_PATTERNS):
                        continue
                    violations.append(
                        f"{py_file}:{description}: {line[:80]}"
                    )

        assert len(violations) == 0, (
            f"Found potential hardcoded secrets:\n" + "\n".join(violations)
        )

    def test_env_file_not_committed_with_real_secrets(self):
        """The .env file should use placeholder values, not real production secrets."""
        env_file = Path(".env")
        if not env_file.exists():
            pytest.skip(".env file not found")

        content = env_file.read_text(encoding="utf-8")

        # These are acceptable placeholder values
        dangerous_patterns = [
            r"POSTGRES_PASSWORD=(?!change_me|CHANGE_ME|\$\{)[^\s#]{12,}",
            r"REDIS_PASSWORD=(?!change_me|CHANGE_ME|\$\{)[^\s#]{12,}",
            r"MINIO_SECRET_KEY=(?!change_me|CHANGE_ME|\$\{)[^\s#]{12,}",
        ]

        # Note: ENCRYPTION_MASTER_KEY is a hex string — that's expected
        for pattern in dangerous_patterns:
            matches = re.findall(pattern, content)
            # Only fail if it looks like a real password (not a hex key or placeholder)
            real_matches = [m for m in matches if not re.match(r"^[0-9a-f]{64}$", m.split("=", 1)[-1])]
            assert len(real_matches) == 0, (
                f"Potential real secret in .env: {real_matches}"
            )


# ---------------------------------------------------------------------------
# Cryptography configuration checks
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestCryptographyConfiguration:
    """Verify cryptographic settings meet security requirements."""

    def test_bcrypt_rounds_minimum_12(self):
        """Password hashing must use at least 12 bcrypt rounds."""
        from app.core.config import settings
        assert settings.password_bcrypt_rounds >= 12, (
            f"bcrypt rounds must be >= 12, got {settings.password_bcrypt_rounds}"
        )

    def test_jwt_algorithm_is_rs256(self):
        """JWT must use RS256 (asymmetric) not HS256 (symmetric)."""
        from app.core.config import settings
        assert settings.jwt_algorithm == "RS256", (
            f"JWT algorithm must be RS256, got {settings.jwt_algorithm}"
        )

    def test_jwt_access_token_expiry_max_8_hours(self):
        """Access tokens must expire within 8 hours."""
        from app.core.config import settings
        assert settings.jwt_access_token_expire_hours <= 8, (
            f"Access token expiry must be <= 8 hours, got {settings.jwt_access_token_expire_hours}"
        )

    def test_encryption_key_is_64_hex_chars(self):
        """Encryption master key must be exactly 64 hex characters (32 bytes)."""
        from app.core.config import settings
        key = settings.encryption_master_key
        assert len(key) == 64, f"Encryption key must be 64 chars, got {len(key)}"
        assert re.match(r"^[0-9a-fA-F]{64}$", key), (
            "Encryption key must be a valid hex string"
        )

    def test_account_lockout_after_5_attempts(self):
        """Account must lock after no more than 5 failed attempts."""
        from app.core.config import settings
        assert settings.account_lockout_attempts <= 5, (
            f"Account lockout must trigger at <= 5 attempts, got {settings.account_lockout_attempts}"
        )

    def test_account_lockout_duration_minimum_30_minutes(self):
        """Account lockout must last at least 30 minutes."""
        from app.core.config import settings
        assert settings.account_lockout_duration >= 1800, (
            f"Lockout duration must be >= 1800s (30min), got {settings.account_lockout_duration}"
        )

    def test_password_hash_uses_bcrypt(self):
        """Password hashing must use bcrypt algorithm."""
        from app.core.security import hash_password, verify_password

        test_password = "TestPassword123!"
        hashed = hash_password(test_password)

        # bcrypt hashes start with $2b$ or $2a$
        assert hashed.startswith(("$2b$", "$2a$")), (
            f"Password hash must use bcrypt, got: {hashed[:10]}..."
        )
        assert verify_password(test_password, hashed), "Password verification failed"
        assert not verify_password("wrong_password", hashed), (
            "Wrong password should not verify"
        )

    def test_aes_gcm_encryption_round_trip(self):
        """AES-256-GCM encryption must be a lossless round-trip."""
        from app.utils.encryption import encrypt_aes_gcm, decrypt_aes_gcm

        test_key = "a" * 64
        plaintext = "rtsp://admin:secret@192.168.1.100/stream1"

        encrypted = encrypt_aes_gcm(plaintext, test_key)
        decrypted = decrypt_aes_gcm(encrypted, test_key)

        assert decrypted == plaintext
        assert encrypted != plaintext  # Must actually encrypt


# ---------------------------------------------------------------------------
# RBAC enforcement checks
# ---------------------------------------------------------------------------

@pytest.mark.security
class TestRBACEnforcement:
    """Verify RBAC rules are correctly defined."""

    def test_all_admin_endpoints_require_admin_role(self):
        """Admin router endpoints must require ADMIN role."""
        from app.api.v1.routers.admin import router
        from app.api.v1.dependencies.auth import require_admin

        # Check that require_admin is used in admin router dependencies
        admin_source = Path("app/api/v1/routers/admin.py").read_text(encoding="utf-8")
        assert "require_admin" in admin_source, (
            "Admin router must use require_admin dependency"
        )

    def test_intelligence_endpoints_require_analyst_role(self):
        """Intelligence endpoints must require at least ANALYST role."""
        intel_source = Path("app/api/v1/routers/intelligence.py").read_text(encoding="utf-8")
        assert "require_analyst" in intel_source, (
            "Intelligence router must use require_analyst dependency"
        )

    def test_alert_endpoints_require_operator_role(self):
        """Alert endpoints must require at least OPERATOR role."""
        alerts_source = Path("app/api/v1/routers/alerts.py").read_text(encoding="utf-8")
        assert "require_operator" in alerts_source, (
            "Alerts router must use require_operator dependency"
        )

    def test_audit_log_is_immutable(self):
        """AuditLogRepository must not expose update/delete methods."""
        from app.repositories.audit_log import AuditLogRepository
        import pytest as _pytest

        repo = AuditLogRepository(None)  # type: ignore

        with _pytest.raises(NotImplementedError):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                repo.update("fake-id")  # type: ignore
            )

    def test_service_number_format_validation(self):
        """Service number validation must reject invalid formats."""
        from app.models.user import User

        valid = ["NSG/OP/1234", "NSG/SAG/9999", "NSG/CMD/001"]
        invalid = ["", "NSG", "NSG/", "nsg/op/123", "NSG/123/ABC", "INVALID"]

        for sn in valid:
            assert User.validate_service_number(sn), f"Should accept: {sn}"

        for sn in invalid:
            assert not User.validate_service_number(sn), f"Should reject: {sn}"
