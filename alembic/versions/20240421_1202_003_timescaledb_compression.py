"""timescaledb_compression

Revision ID: 003
Revises: 002
Create Date: 2024-04-21 12:02:00.000000

TimescaleDB compression policy — skipped gracefully if TimescaleDB is not installed.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_timescaledb() -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'timescaledb'")
    )
    return result.scalar() > 0


def upgrade() -> None:
    if not _has_timescaledb():
        print("  [SKIP] TimescaleDB not installed — skipping compression policy")
        return

    op.execute("""
        ALTER TABLE detection_events SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'feed_id',
            timescaledb.compress_orderby = 'frame_timestamp DESC'
        )
    """)
    op.execute(
        "SELECT add_compression_policy('detection_events', INTERVAL '7 days')"
    )
    op.execute("""
        COMMENT ON TABLE detection_events IS
        'TimescaleDB hypertable with automatic compression after 7 days, segmented by feed_id.'
    """)


def downgrade() -> None:
    if not _has_timescaledb():
        return
    op.execute(
        "SELECT remove_compression_policy('detection_events', if_exists => true)"
    )
    op.execute(
        "ALTER TABLE detection_events SET (timescaledb.compress = false)"
    )
    op.execute("COMMENT ON TABLE detection_events IS NULL")
