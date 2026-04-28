"""initial_schema

Revision ID: 001
Revises:
Create Date: 2024-04-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _try_execute(sql: str, description: str = "") -> None:
    """Execute SQL, silently skip if extension/feature not available."""
    try:
        op.execute(sql)
    except Exception as e:
        print(f"  [SKIP] {description or sql[:60]}: {e}")


def upgrade() -> None:
    """Create all tables. pgvector and TimescaleDB are optional."""

    # Extensions are pre-installed via scripts/setup_db.sql
    # We check what's available but don't try to CREATE EXTENSION here
    # (CREATE EXTENSION in a transaction causes abort on failure)

    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('service_number', sa.String(50), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('unit', sa.String(100), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "role IN ('OPERATOR', 'ANALYST', 'COMMANDER', 'ADMIN')",
            name='check_user_role_valid'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_number'),
    )
    op.create_index('idx_users_service_number', 'users', ['service_number'])
    op.create_index('idx_users_role', 'users', ['role'])

    # ── security_zones ────────────────────────────────────────────────────
    op.create_table(
        'security_zones',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('zone_type', sa.String(50), nullable=False),
        sa.Column('polygon_coordinates', postgresql.JSONB(), nullable=False,
                  server_default='[]'),
        sa.Column('threat_level', sa.String(20), nullable=False,
                  server_default='GREEN'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "zone_type IN ('PERIMETER', 'RESTRICTED', 'PUBLIC', 'INNER_CORDON')",
            name='check_zone_type_valid'),
        sa.CheckConstraint(
            "threat_level IN ('GREEN', 'AMBER', 'RED', 'CRITICAL')",
            name='check_threat_level_valid'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_zones_threat_level', 'security_zones', ['threat_level'])

    # ── video_feeds ───────────────────────────────────────────────────────
    op.create_table(
        'video_feeds',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('feed_type', sa.String(50), nullable=False),
        sa.Column('rtsp_url_encrypted', sa.Text(), nullable=False),
        sa.Column('location_name', sa.String(255), nullable=True),
        sa.Column('latitude', sa.Numeric(10, 8), nullable=True),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='OFFLINE'),
        sa.Column('resolution', sa.String(20), nullable=True),
        sa.Column('fps', sa.Integer(), nullable=True),
        sa.Column('codec', sa.String(20), nullable=True),
        sa.Column('ai_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ai_processing_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "feed_type IN ('FIXED_CAMERA', 'DRONE', 'BODY_CAM', 'LEGACY_CCTV')",
            name='check_feed_type_valid'),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'OFFLINE', 'DEGRADED', 'MAINTENANCE')",
            name='check_feed_status_valid'),
        sa.ForeignKeyConstraint(['zone_id'], ['security_zones.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_feeds_zone', 'video_feeds', ['zone_id'])
    op.create_index('idx_feeds_status', 'video_feeds', ['status'])
    op.create_index('idx_feeds_type', 'video_feeds', ['feed_type'])

    # ── watchlist_entries (face_embedding as JSONB if pgvector absent) ────
    # Detect whether pgvector is available
    conn = op.get_bind()
    has_vector = conn.execute(
        sa.text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'")
    ).scalar() > 0

    if has_vector:
        from pgvector.sqlalchemy import Vector
        face_embedding_col = sa.Column('face_embedding', Vector(512), nullable=True)
    else:
        face_embedding_col = sa.Column('face_embedding', postgresql.JSONB(), nullable=True)

    op.create_table(
        'watchlist_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('alias', sa.String(255), nullable=True),
        sa.Column('threat_category', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('nationality', sa.String(100), nullable=True),
        sa.Column('known_associates', sa.Text(), nullable=True),
        sa.Column('face_images', postgresql.JSONB(), nullable=True),
        face_embedding_col,
        sa.Column('status', sa.String(20), nullable=False,
                  server_default='PENDING_APPROVAL'),
        sa.Column('source_agency', sa.String(100), nullable=True),
        sa.Column('added_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "threat_category IN ('KNOWN_TERRORIST', 'SUSPECT', 'POI', 'BANNED')",
            name='check_threat_category_valid'),
        sa.CheckConstraint(
            "status IN ('PENDING_APPROVAL', 'ACTIVE', 'DEACTIVATED')",
            name='check_watchlist_status_valid'),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_watchlist_status', 'watchlist_entries', ['status'])
    if has_vector:
        _try_execute(
            "CREATE INDEX idx_watchlist_face_embedding ON watchlist_entries "
            "USING ivfflat (face_embedding vector_cosine_ops) WITH (lists = 100)",
            "pgvector ivfflat index"
        )

    # ── tracked_persons ───────────────────────────────────────────────────
    if has_vector:
        from pgvector.sqlalchemy import Vector
        tp_embedding_col = sa.Column('face_embedding', Vector(512), nullable=True)
    else:
        tp_embedding_col = sa.Column('face_embedding', postgresql.JSONB(), nullable=True)

    op.create_table(
        'tracked_persons',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('track_id', sa.String(100), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('feed_ids_seen', postgresql.JSONB(), nullable=True),
        tp_embedding_col,
        sa.Column('operator_label', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('watchlist_match', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('watchlist_entry_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('trajectory', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "operator_label IN ('SUSPECT', 'CIVILIAN', 'FRIENDLY', 'UNKNOWN')",
            name='check_operator_label_valid'),
        sa.ForeignKeyConstraint(
            ['watchlist_entry_id'], ['watchlist_entries.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('track_id'),
    )
    op.create_index('idx_tracked_persons_track_id', 'tracked_persons', ['track_id'])
    op.create_index('idx_tracked_persons_watchlist_match', 'tracked_persons', ['watchlist_match'])
    op.create_index('idx_tracked_persons_last_seen', 'tracked_persons', ['last_seen_at'])

    # ── detection_events ──────────────────────────────────────────────────
    has_timescale = conn.execute(
        sa.text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'timescaledb'")
    ).scalar() > 0

    op.create_table(
        'detection_events',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('frame_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('feed_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('detection_type', sa.String(50), nullable=False),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False),
        sa.Column('bounding_box', postgresql.JSONB(), nullable=False,
                  server_default='{}'),
        sa.Column('object_class', sa.String(100), nullable=True),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('watchlist_match_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('threat_level', sa.String(20), nullable=True),
        sa.Column('operator_label', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('frame_snapshot_path', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "detection_type IN ('FACE', 'OBJECT', 'VEHICLE', 'ANOMALY', 'ZONE_BREACH', 'LICENSE_PLATE', 'WEAPON')",
            name='check_detection_type_valid'),
        sa.CheckConstraint(
            "threat_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name='check_detection_threat_level_valid'),
        sa.CheckConstraint(
            "operator_label IN ('SUSPECT', 'CIVILIAN', 'FRIENDLY', 'UNKNOWN')",
            name='check_detection_operator_label_valid'),
        sa.CheckConstraint(
            'confidence_score >= 0.0 AND confidence_score <= 1.0',
            name='check_confidence_score_range'),
        sa.ForeignKeyConstraint(['feed_id'], ['video_feeds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['tracked_persons.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(
            ['watchlist_match_id'], ['watchlist_entries.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', 'frame_timestamp'),
    )

    if has_timescale:
        _try_execute(
            "SELECT create_hypertable('detection_events', 'frame_timestamp')",
            "TimescaleDB hypertable"
        )

    op.create_index('idx_detection_events_feed', 'detection_events',
                    ['feed_id', 'frame_timestamp'])
    op.create_index('idx_detection_events_type', 'detection_events', ['detection_type'])
    op.create_index('idx_detection_events_person', 'detection_events', ['person_id'])
    op.create_index('idx_detection_events_watchlist', 'detection_events', ['watchlist_match_id'])

    # ── alerts ────────────────────────────────────────────────────────────
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('detection_event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
        sa.Column('feed_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('false_positive_reason', sa.Text(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='1'),
        sa.CheckConstraint(
            "alert_type IN ('WATCHLIST_MATCH', 'ZONE_BREACH', 'WEAPON_DETECTED', "
            "'UNATTENDED_OBJECT', 'CROWD_ANOMALY', 'LOITERING', 'VEHICLE_THREAT')",
            name='check_alert_type_valid'),
        sa.CheckConstraint(
            "priority IN ('P1_CRITICAL', 'P2_HIGH', 'P3_MEDIUM', 'P4_LOW')",
            name='check_alert_priority_valid'),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'FALSE_POSITIVE')",
            name='check_alert_status_valid'),
        sa.ForeignKeyConstraint(['feed_id'], ['video_feeds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['zone_id'], ['security_zones.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_alerts_status', 'alerts', ['status'])
    op.create_index('idx_alerts_priority', 'alerts', ['priority'])
    op.create_index('idx_alerts_triggered_at', 'alerts', ['triggered_at'])
    op.create_index('idx_alerts_feed', 'alerts', ['feed_id'])
    op.create_index('idx_alerts_zone', 'alerts', ['zone_id'])
    op.create_index('idx_alerts_type', 'alerts', ['alert_type'])

    # ── video_segments ────────────────────────────────────────────────────
    op.create_table(
        'video_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('feed_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('encryption_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('has_flagged_events', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('retention_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['feed_id'], ['video_feeds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_video_segments_feed_start', 'video_segments',
                    ['feed_id', 'start_timestamp'])
    op.create_index('idx_video_segments_retention', 'video_segments', ['retention_until'])

    # ── ml_models ─────────────────────────────────────────────────────────
    op.create_table(
        'ml_models',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('framework', sa.String(20), nullable=False),
        sa.Column('weights_path', sa.Text(), nullable=False),
        sa.Column('config_path', sa.Text(), nullable=True),
        sa.Column('accuracy_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deployed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "model_type IN ('DETECTION', 'TRACKING', 'FACE_RECOGNITION', 'ANOMALY')",
            name='check_model_type_valid'),
        sa.CheckConstraint(
            "framework IN ('pytorch', 'onnx', 'tensorrt')",
            name='check_framework_valid'),
        sa.ForeignKeyConstraint(['deployed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ml_models_type', 'ml_models', ['model_type'])
    op.create_index('idx_ml_models_active', 'ml_models', ['is_active'])

    # ── audit_logs ────────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),   # INET as string for compat
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])

    # ── reports ───────────────────────────────────────────────────────────
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('classification', sa.String(20), nullable=False),
        sa.Column('detection_event_ids', postgresql.JSONB(), nullable=True),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.CheckConstraint(
            "report_type IN ('INCIDENT_REPORT', 'PERSON_REPORT', 'ZONE_ACTIVITY', "
            "'OPERATION_SUMMARY', 'FORENSIC_TIMELINE')",
            name='check_report_type_valid'),
        sa.CheckConstraint(
            "classification IN ('RESTRICTED', 'CONFIDENTIAL', 'SECRET')",
            name='check_classification_valid'),
        sa.CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'FAILED')",
            name='check_report_status_valid'),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_reports_generated_by', 'reports', ['generated_by'])
    op.create_index('idx_reports_generated_at', 'reports', ['generated_at'])

    # ── forensic_jobs ─────────────────────────────────────────────────────
    op.create_table(
        'forensic_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('search_params', postgresql.JSONB(), nullable=False,
                  server_default='{}'),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('result_count', sa.Integer(), nullable=True),
        sa.Column('results', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.CheckConstraint(
            "job_type IN ('FACE_SEARCH', 'OBJECT_SEARCH', 'ZONE_SEARCH', 'TIMELINE_SEARCH')",
            name='check_job_type_valid'),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name='check_forensic_job_status_valid'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_forensic_jobs_created_by', 'forensic_jobs', ['created_by'])
    op.create_index('idx_forensic_jobs_status', 'forensic_jobs', ['status'])


def downgrade() -> None:
    """Drop all tables."""
    for table in [
        'forensic_jobs', 'reports', 'audit_logs', 'ml_models',
        'video_segments', 'alerts', 'detection_events',
        'tracked_persons', 'watchlist_entries', 'video_feeds',
        'security_zones', 'users',
    ]:
        op.drop_table(table)
