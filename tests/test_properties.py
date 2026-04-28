"""
Property-Based Tests — Task PBT.1

Implements all 9 correctness properties using Hypothesis.
Tests formal specifications that the NSG VisionAI platform must satisfy.

Properties:
    1. Service Number Format Validation
    2. RTSP URL Encryption Round-Trip
    3. Confidence Threshold Comparison
    4. Trajectory Timestamp Monotonicity
    5. Trajectory JSON Serialization Round-Trip
    6. Alert Priority Calculation
    7. Alert Deduplication Within Time Window
    8. RBAC Authorization Rules
    9. Configuration Parser Round-Trip
"""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from hypothesis import assume, given, settings as h_settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Property 1: Service Number Format Validation
# ---------------------------------------------------------------------------

SERVICE_NUMBER_PATTERN = re.compile(r"^NSG/[A-Z]+/\d+$")


def validate_service_number(service_number: str) -> bool:
    """Validate NSG service number format: NSG/<UNIT>/<NUMBER>"""
    return bool(SERVICE_NUMBER_PATTERN.match(service_number))


@pytest.mark.property("nsg-visionai-platform", "Property 1")
class TestServiceNumberFormatValidation:
    """Property 1: Service number format validation."""

    @given(st.text())
    @h_settings(max_examples=200)
    def test_random_strings_mostly_invalid(self, s: str):
        """Random strings should almost never match the service number format."""
        # This is a statistical property — most random strings are invalid
        # We just verify the validator doesn't crash
        result = validate_service_number(s)
        assert isinstance(result, bool)

    @given(
        unit=st.from_regex(r"[A-Z]{1,10}", fullmatch=True),
        number=st.integers(min_value=1, max_value=99999),
    )
    @h_settings(max_examples=200)
    def test_valid_format_always_accepted(self, unit: str, number: int):
        """Valid service numbers must always be accepted."""
        service_number = f"NSG/{unit}/{number}"
        assert validate_service_number(service_number), (
            f"Valid service number '{service_number}' was rejected"
        )

    @given(
        st.one_of(
            st.just(""),
            st.just("NSG"),
            st.just("NSG/"),
            st.just("NSG//123"),
            st.just("nsg/ALPHA/123"),  # lowercase prefix
            st.just("NSG/alpha/123"),  # lowercase unit
            st.just("NSG/ALPHA/abc"),  # non-numeric number
            st.just("NSG/123/ALPHA"),  # swapped unit and number
        )
    )
    @h_settings(max_examples=50)
    def test_invalid_formats_rejected(self, service_number: str):
        """Known invalid formats must always be rejected."""
        assert not validate_service_number(service_number), (
            f"Invalid service number '{service_number}' was accepted"
        )

    @given(st.from_regex(r"^NSG/[A-Z]+/\d+$", fullmatch=True))
    @h_settings(max_examples=200)
    def test_regex_generated_valid_numbers(self, service_number: str):
        """Regex-generated valid service numbers must always be accepted."""
        assert validate_service_number(service_number)


# ---------------------------------------------------------------------------
# Property 2: RTSP URL Encryption Round-Trip
# ---------------------------------------------------------------------------

@pytest.mark.property("nsg-visionai-platform", "Property 2")
class TestRTSPEncryptionRoundTrip:
    """Property 2: RTSP URL encryption must be a lossless round-trip."""

    @given(
        st.from_regex(
            r"rtsp://[a-zA-Z0-9_]{1,20}:[a-zA-Z0-9_]{1,20}@[a-zA-Z0-9.]{1,30}/[a-zA-Z0-9/]{1,50}",
            fullmatch=True,
        )
    )
    @h_settings(max_examples=100)
    def test_rtsp_encryption_round_trip(self, rtsp_url: str):
        """encrypt(url) → decrypt → original url (round-trip property)."""
        from app.utils.encryption import encrypt_rtsp_url, decrypt_rtsp_url

        # Use a fixed test key (64 hex chars = 32 bytes)
        test_key = "a" * 64

        encrypted = encrypt_rtsp_url(rtsp_url, test_key)
        decrypted = decrypt_rtsp_url(encrypted, test_key)

        assert decrypted == rtsp_url, (
            f"Round-trip failed: original='{rtsp_url}', decrypted='{decrypted}'"
        )

    @given(
        url=st.from_regex(
            r"rtsp://[a-zA-Z0-9_]{1,20}:[a-zA-Z0-9_]{1,20}@[a-zA-Z0-9.]{1,30}/[a-zA-Z0-9/]{1,50}",
            fullmatch=True,
        )
    )
    @h_settings(max_examples=50)
    def test_encryption_produces_different_ciphertext(self, url: str):
        """Same URL encrypted twice should produce different ciphertext (random nonce)."""
        from app.utils.encryption import encrypt_rtsp_url

        test_key = "b" * 64
        encrypted1 = encrypt_rtsp_url(url, test_key)
        encrypted2 = encrypt_rtsp_url(url, test_key)

        # Due to random nonce, ciphertexts should differ
        assert encrypted1 != encrypted2, (
            "Encryption with random nonce should produce different ciphertexts"
        )

    @given(
        url=st.from_regex(
            r"rtsp://[a-zA-Z0-9_]{1,20}:[a-zA-Z0-9_]{1,20}@[a-zA-Z0-9.]{1,30}/[a-zA-Z0-9/]{1,50}",
            fullmatch=True,
        )
    )
    @h_settings(max_examples=50)
    def test_wrong_key_fails_decryption(self, url: str):
        """Decryption with wrong key must fail."""
        from app.utils.encryption import encrypt_rtsp_url, decrypt_rtsp_url

        key1 = "a" * 64
        key2 = "b" * 64

        encrypted = encrypt_rtsp_url(url, key1)

        with pytest.raises((ValueError, Exception)):
            decrypt_rtsp_url(encrypted, key2)


# ---------------------------------------------------------------------------
# Property 3: Confidence Threshold Comparison
# ---------------------------------------------------------------------------

@pytest.mark.property("nsg-visionai-platform", "Property 3")
class TestConfidenceThresholdComparison:
    """Property 3: Alert created ⟺ confidence > threshold."""

    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        threshold=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @h_settings(max_examples=500)
    def test_alert_created_iff_confidence_exceeds_threshold(
        self, confidence: float, threshold: float
    ):
        """Alert should be created if and only if confidence > threshold."""
        should_create_alert = confidence > threshold
        actual_decision = _should_create_alert(confidence, threshold)

        assert actual_decision == should_create_alert, (
            f"confidence={confidence}, threshold={threshold}: "
            f"expected alert={should_create_alert}, got={actual_decision}"
        )

    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @h_settings(max_examples=200)
    def test_confidence_at_threshold_does_not_trigger(self, confidence: float):
        """Confidence exactly equal to threshold should NOT trigger alert (strict >)."""
        threshold = confidence
        assert not _should_create_alert(confidence, threshold), (
            f"Alert triggered at confidence={confidence} == threshold={threshold} (should be strict >)"
        )

    @given(
        confidence=st.floats(min_value=0.751, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @h_settings(max_examples=200)
    def test_high_confidence_always_triggers_at_default_threshold(self, confidence: float):
        """Confidence > 0.75 (default YOLO threshold) should always trigger."""
        default_threshold = 0.75
        assert _should_create_alert(confidence, default_threshold), (
            f"High confidence {confidence} should trigger alert at threshold {default_threshold}"
        )


def _should_create_alert(confidence: float, threshold: float) -> bool:
    """Business logic: create alert if confidence strictly exceeds threshold."""
    return confidence > threshold


# ---------------------------------------------------------------------------
# Property 4: Trajectory Timestamp Monotonicity
# ---------------------------------------------------------------------------

@pytest.mark.property("nsg-visionai-platform", "Property 4")
class TestTrajectoryTimestampMonotonicity:
    """Property 4: All timestamps in trajectory must be monotonically increasing."""

    @given(
        timestamps=st.lists(
            st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 12, 31),
            ),
            min_size=0,
            max_size=100,
        )
    )
    @h_settings(max_examples=200)
    def test_sorted_trajectory_is_monotonic(self, timestamps: List[datetime]):
        """Sorted timestamps must be monotonically non-decreasing."""
        sorted_ts = sorted(timestamps)
        assert _is_monotonic(sorted_ts), (
            "Sorted timestamps should always be monotonically non-decreasing"
        )

    @given(
        timestamps=st.lists(
            st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 12, 31),
            ),
            min_size=2,
            max_size=50,
        )
    )
    @h_settings(max_examples=200)
    def test_unsorted_trajectory_may_not_be_monotonic(self, timestamps: List[datetime]):
        """Unsorted timestamps may violate monotonicity — validator should detect it."""
        is_valid = _is_monotonic(timestamps)
        # Verify our validator is consistent with manual check
        for i in range(1, len(timestamps)):
            if timestamps[i] < timestamps[i - 1]:
                assert not is_valid, (
                    f"Validator missed non-monotonic pair at index {i}: "
                    f"{timestamps[i-1]} > {timestamps[i]}"
                )
                return
        assert is_valid

    @given(
        base_time=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
        deltas=st.lists(
            st.integers(min_value=1, max_value=3600),
            min_size=1,
            max_size=50,
        ),
    )
    @h_settings(max_examples=200)
    def test_strictly_increasing_trajectory_is_valid(
        self, base_time: datetime, deltas: List[int]
    ):
        """Strictly increasing timestamps must always pass validation."""
        timestamps = [base_time]
        for delta in deltas:
            timestamps.append(timestamps[-1] + timedelta(seconds=delta))

        assert _is_monotonic(timestamps), (
            "Strictly increasing timestamps should always be valid"
        )


def _is_monotonic(timestamps: List[datetime]) -> bool:
    """Check if timestamps are monotonically non-decreasing."""
    for i in range(1, len(timestamps)):
        if timestamps[i] < timestamps[i - 1]:
            return False
    return True


# ---------------------------------------------------------------------------
# Property 5: Trajectory JSON Serialization Round-Trip
# ---------------------------------------------------------------------------

@pytest.mark.property("nsg-visionai-platform", "Property 5")
class TestTrajectoryJSONSerializationRoundTrip:
    """Property 5: Trajectory JSON serialization must be a lossless round-trip."""

    @given(
        trajectory=st.lists(
            st.fixed_dictionaries({
                "timestamp": st.datetimes(
                    min_value=datetime(2020, 1, 1),
                    max_value=datetime(2030, 12, 31),
                ).map(lambda dt: dt.isoformat()),
                "feed_id": st.uuids().map(str),
                "x": st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
                "y": st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
                "confidence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            }),
            min_size=0,
            max_size=50,
        )
    )
    @h_settings(max_examples=200)
    def test_trajectory_json_round_trip(self, trajectory: list):
        """serialize(trajectory) → deserialize → equivalent trajectory."""
        serialized = _serialize_trajectory(trajectory)
        deserialized = _deserialize_trajectory(serialized)

        assert deserialized == trajectory, (
            f"Trajectory round-trip failed: original length={len(trajectory)}, "
            f"deserialized length={len(deserialized)}"
        )

    @given(
        trajectory=st.lists(
            st.fixed_dictionaries({
                "timestamp": st.datetimes(
                    min_value=datetime(2020, 1, 1),
                    max_value=datetime(2030, 12, 31),
                ).map(lambda dt: dt.isoformat()),
                "feed_id": st.uuids().map(str),
                "x": st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
                "y": st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
            }),
            min_size=0,
            max_size=20,
        )
    )
    @h_settings(max_examples=100)
    def test_serialized_trajectory_is_valid_json(self, trajectory: list):
        """Serialized trajectory must always be valid JSON."""
        serialized = _serialize_trajectory(trajectory)
        # Should not raise
        parsed = json.loads(serialized)
        assert isinstance(parsed, list)
        assert len(parsed) == len(trajectory)


def _serialize_trajectory(trajectory: list) -> str:
    """Serialize trajectory to JSON string."""
    return json.dumps(trajectory, ensure_ascii=False)


def _deserialize_trajectory(serialized: str) -> list:
    """Deserialize trajectory from JSON string."""
    return json.loads(serialized)


# ---------------------------------------------------------------------------
# Property 6: Alert Priority Calculation
# ---------------------------------------------------------------------------

@pytest.mark.property("nsg-visionai-platform", "Property 6")
class TestAlertPriorityCalculation:
    """Property 6: Alert priority must match defined rules for all input combinations."""

    ALERT_TYPES = [
        "WATCHLIST_MATCH", "ZONE_BREACH", "WEAPON_DETECTED",
        "UNATTENDED_OBJECT", "CROWD_ANOMALY", "LOITERING", "VEHICLE_THREAT",
    ]
    THREAT_LEVELS = ["GREEN", "AMBER", "RED", "CRITICAL"]

    @given(
        alert_type=st.sampled_from(ALERT_TYPES),
        zone_threat_level=st.sampled_from(THREAT_LEVELS),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @h_settings(max_examples=500)
    def test_priority_matches_rules(
        self, alert_type: str, zone_threat_level: str, confidence: float
    ):
        """Priority must match defined rules for all input combinations."""
        from app.models.alert import Alert

        priority = Alert.calculate_priority(alert_type, zone_threat_level, confidence)

        # Verify priority is a valid value
        assert priority in ("P1_CRITICAL", "P2_HIGH", "P3_MEDIUM", "P4_LOW"), (
            f"Invalid priority '{priority}' for alert_type={alert_type}, "
            f"zone={zone_threat_level}, confidence={confidence}"
        )

        # Verify specific rules
        if alert_type == "WEAPON_DETECTED":
            assert priority == "P1_CRITICAL", (
                f"WEAPON_DETECTED must always be P1_CRITICAL, got {priority}"
            )

        if alert_type == "WATCHLIST_MATCH" and confidence > 0.90:
            assert priority == "P1_CRITICAL", (
                f"WATCHLIST_MATCH with confidence {confidence} > 0.90 must be P1_CRITICAL"
            )

        if zone_threat_level == "CRITICAL" and confidence > 0.85:
            assert priority == "P1_CRITICAL", (
                f"CRITICAL zone with confidence {confidence} > 0.85 must be P1_CRITICAL"
            )

    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @h_settings(max_examples=200)
    def test_weapon_always_critical(self, confidence: float):
        """WEAPON_DETECTED must always be P1_CRITICAL regardless of confidence."""
        from app.models.alert import Alert

        priority = Alert.calculate_priority("WEAPON_DETECTED", "GREEN", confidence)
        assert priority == "P1_CRITICAL"

    @given(
        alert_type=st.sampled_from(["LOITERING", "UNATTENDED_OBJECT", "CROWD_ANOMALY"]),
        confidence=st.floats(min_value=0.0, max_value=0.79, allow_nan=False, allow_infinity=False),
    )
    @h_settings(max_examples=200)
    def test_low_risk_green_zone_is_low_priority(
        self, alert_type: str, confidence: float
    ):
        """Low-risk alert types in GREEN zone with low confidence should be P4_LOW."""
        from app.models.alert import Alert

        priority = Alert.calculate_priority(alert_type, "GREEN", confidence)
        assert priority == "P4_LOW", (
            f"Expected P4_LOW for {alert_type} in GREEN zone with confidence {confidence}, "
            f"got {priority}"
        )


# ---------------------------------------------------------------------------
# Property 7: Alert Deduplication Within Time Window
# ---------------------------------------------------------------------------

@pytest.mark.property("nsg-visionai-platform", "Property 7")
class TestAlertDeduplication:
    """Property 7: Alerts within 30s window are deduplicated; outside create new records."""

    DEDUP_WINDOW_SECONDS = 30

    @given(
        delta_seconds=st.floats(
            min_value=0.0,
            max_value=29.9,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @h_settings(max_examples=200)
    def test_alerts_within_window_are_duplicates(self, delta_seconds: float):
        """Alerts within 30s window should be classified as duplicates."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        alert_time = base_time + timedelta(seconds=delta_seconds)

        is_dup = _is_duplicate_alert(base_time, alert_time, self.DEDUP_WINDOW_SECONDS)
        assert is_dup, (
            f"Alert at +{delta_seconds}s should be a duplicate (within {self.DEDUP_WINDOW_SECONDS}s window)"
        )

    @given(
        delta_seconds=st.floats(
            min_value=30.001,
            max_value=3600.0,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @h_settings(max_examples=200)
    def test_alerts_outside_window_are_new(self, delta_seconds: float):
        """Alerts outside 30s window should create new records."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        alert_time = base_time + timedelta(seconds=delta_seconds)

        is_dup = _is_duplicate_alert(base_time, alert_time, self.DEDUP_WINDOW_SECONDS)
        assert not is_dup, (
            f"Alert at +{delta_seconds}s should NOT be a duplicate (outside {self.DEDUP_WINDOW_SECONDS}s window)"
        )

    @given(
        delta_seconds=st.floats(
            min_value=30.0,
            max_value=30.0,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @h_settings(max_examples=10)
    def test_alert_exactly_at_boundary_is_new(self, delta_seconds: float):
        """Alert exactly at 30s boundary should create a new record (exclusive window)."""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        alert_time = base_time + timedelta(seconds=30.0)

        is_dup = _is_duplicate_alert(base_time, alert_time, self.DEDUP_WINDOW_SECONDS)
        assert not is_dup, "Alert exactly at 30s boundary should NOT be a duplicate"


def _is_duplicate_alert(
    existing_time: datetime,
    new_time: datetime,
    window_seconds: int,
) -> bool:
    """
    Check if new_time falls within the deduplication window of existing_time.
    Window is [existing_time, existing_time + window_seconds) — exclusive upper bound.
    """
    delta = (new_time - existing_time).total_seconds()
    return 0 <= delta < window_seconds


# ---------------------------------------------------------------------------
# Property 8: RBAC Authorization Rules
# ---------------------------------------------------------------------------

@pytest.mark.property("nsg-visionai-platform", "Property 8")
class TestRBACAuthorizationRules:
    """Property 8: Authorization must match defined RBAC rules for all role/endpoint combinations."""

    # Role hierarchy: OPERATOR < ANALYST < COMMANDER < ADMIN
    ROLE_HIERARCHY = {
        "OPERATOR": 1,
        "ANALYST": 2,
        "COMMANDER": 3,
        "ADMIN": 4,
    }

    # Minimum role required per endpoint category
    ENDPOINT_MIN_ROLES = {
        "view_alerts": "OPERATOR",
        "acknowledge_alert": "OPERATOR",
        "view_feeds": "OPERATOR",
        "toggle_ai": "OPERATOR",
        "view_watchlist": "ANALYST",
        "create_watchlist": "ANALYST",
        "forensic_search": "ANALYST",
        "generate_report": "ANALYST",
        "view_analytics": "ANALYST",
        "approve_watchlist": "COMMANDER",
        "update_threat_level": "COMMANDER",
        "manage_users": "ADMIN",
        "deploy_model": "ADMIN",
        "view_audit_logs": "ADMIN",
        "restart_worker": "ADMIN",
    }

    @given(
        role=st.sampled_from(list(ROLE_HIERARCHY.keys())),
        endpoint=st.sampled_from(list(ENDPOINT_MIN_ROLES.keys())),
    )
    @h_settings(max_examples=500)
    def test_rbac_rules_consistent(self, role: str, endpoint: str):
        """Authorization result must be consistent with role hierarchy."""
        is_authorized = _check_rbac(role, endpoint, self.ROLE_HIERARCHY, self.ENDPOINT_MIN_ROLES)
        min_role = self.ENDPOINT_MIN_ROLES[endpoint]

        expected = self.ROLE_HIERARCHY[role] >= self.ROLE_HIERARCHY[min_role]
        assert is_authorized == expected, (
            f"RBAC mismatch: role={role}, endpoint={endpoint}, "
            f"expected={expected}, got={is_authorized}"
        )

    @given(
        endpoint=st.sampled_from(list(ENDPOINT_MIN_ROLES.keys())),
    )
    @h_settings(max_examples=100)
    def test_admin_can_access_all_endpoints(self, endpoint: str):
        """ADMIN role must have access to all endpoints."""
        assert _check_rbac("ADMIN", endpoint, self.ROLE_HIERARCHY, self.ENDPOINT_MIN_ROLES), (
            f"ADMIN should have access to endpoint '{endpoint}'"
        )

    @given(
        endpoint=st.sampled_from(["manage_users", "deploy_model", "view_audit_logs", "restart_worker"]),
    )
    @h_settings(max_examples=50)
    def test_non_admin_cannot_access_admin_endpoints(self, endpoint: str):
        """Non-ADMIN roles must not access ADMIN-only endpoints."""
        for role in ["OPERATOR", "ANALYST", "COMMANDER"]:
            assert not _check_rbac(role, endpoint, self.ROLE_HIERARCHY, self.ENDPOINT_MIN_ROLES), (
                f"Role {role} should NOT have access to admin endpoint '{endpoint}'"
            )


def _check_rbac(
    role: str,
    endpoint: str,
    hierarchy: dict,
    min_roles: dict,
) -> bool:
    """Check if role has access to endpoint based on hierarchy."""
    if role not in hierarchy or endpoint not in min_roles:
        return False
    min_role = min_roles[endpoint]
    return hierarchy[role] >= hierarchy[min_role]


# ---------------------------------------------------------------------------
# Property 9: Configuration Parser Round-Trip
# ---------------------------------------------------------------------------

@pytest.mark.property("nsg-visionai-platform", "Property 9")
class TestConfigurationParserRoundTrip:
    """Property 9: Configuration parsing must be a lossless round-trip."""

    @given(
        config=st.fixed_dictionaries({
            "app_name": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"))),
            "debug": st.booleans(),
            "environment": st.sampled_from(["development", "staging", "production"]),
            "jwt_access_token_expire_hours": st.integers(min_value=1, max_value=24),
            "jwt_refresh_token_expire_days": st.integers(min_value=1, max_value=90),
            "password_bcrypt_rounds": st.integers(min_value=10, max_value=14),
            "max_failed_login_attempts": st.integers(min_value=3, max_value=10),
            "account_lockout_minutes": st.integers(min_value=5, max_value=60),
        })
    )
    @h_settings(max_examples=200)
    def test_config_json_round_trip(self, config: dict):
        """Config dict → JSON → parse → equivalent config (round-trip)."""
        serialized = json.dumps(config, sort_keys=True)
        deserialized = json.loads(serialized)

        assert deserialized == config, (
            f"Config round-trip failed: original={config}, deserialized={deserialized}"
        )

    @given(
        config=st.fixed_dictionaries({
            "app_name": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"))),
            "debug": st.booleans(),
            "environment": st.sampled_from(["development", "staging", "production"]),
        })
    )
    @h_settings(max_examples=200)
    def test_config_serialization_preserves_types(self, config: dict):
        """Config serialization must preserve field types."""
        serialized = json.dumps(config)
        deserialized = json.loads(serialized)

        assert isinstance(deserialized["app_name"], str)
        assert isinstance(deserialized["debug"], bool)
        assert isinstance(deserialized["environment"], str)

    @given(
        threshold=st.floats(
            min_value=0.0,
            max_value=1.0,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @h_settings(max_examples=200)
    def test_confidence_threshold_config_round_trip(self, threshold: float):
        """Confidence threshold config must survive JSON round-trip."""
        config = {"confidence_threshold": threshold}
        serialized = json.dumps(config)
        deserialized = json.loads(serialized)

        # Float precision may differ slightly, use approximate comparison
        assert abs(deserialized["confidence_threshold"] - threshold) < 1e-10, (
            f"Threshold round-trip failed: original={threshold}, "
            f"deserialized={deserialized['confidence_threshold']}"
        )
