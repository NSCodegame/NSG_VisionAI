"""
Analytics Service — Phase 19, Task 19.1

Provides mission analytics, trend analysis, and ML performance metrics.
Uses TimescaleDB time-bucket queries for efficiency.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertPriority, AlertStatus, AlertType
from app.models.detection_event import DetectionEvent
from app.models.tracked_person import TrackedPerson
from app.models.watchlist_entry import WatchlistEntry

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for mission analytics and trend analysis.
    Implements all analytics endpoints from Phase 19.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_summary(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get high-level mission summary metrics.

        Returns:
            Dict with total alerts by priority, watchlist matches, zone breaches,
            persons tracked, false positive rate, and avg detection latency.
        """
        if to_dt is None:
            to_dt = datetime.utcnow()
        if from_dt is None:
            from_dt = to_dt - timedelta(days=7)

        # Total alerts by priority
        alerts_by_priority = {}
        for priority in AlertPriority:
            count_result = await self.session.execute(
                select(func.count(Alert.id)).where(
                    Alert.triggered_at >= from_dt,
                    Alert.triggered_at <= to_dt,
                    Alert.priority == priority.value,
                )
            )
            alerts_by_priority[priority.value] = count_result.scalar() or 0

        # Total alerts
        total_alerts_result = await self.session.execute(
            select(func.count(Alert.id)).where(
                Alert.triggered_at >= from_dt,
                Alert.triggered_at <= to_dt,
            )
        )
        total_alerts = total_alerts_result.scalar() or 0

        # Watchlist matches
        watchlist_matches_result = await self.session.execute(
            select(func.count(Alert.id)).where(
                Alert.triggered_at >= from_dt,
                Alert.triggered_at <= to_dt,
                Alert.alert_type == AlertType.WATCHLIST_MATCH.value,
            )
        )
        watchlist_matches = watchlist_matches_result.scalar() or 0

        # Zone breaches
        zone_breaches_result = await self.session.execute(
            select(func.count(Alert.id)).where(
                Alert.triggered_at >= from_dt,
                Alert.triggered_at <= to_dt,
                Alert.alert_type == AlertType.ZONE_BREACH.value,
            )
        )
        zone_breaches = zone_breaches_result.scalar() or 0

        # Persons tracked (active in period)
        persons_tracked_result = await self.session.execute(
            select(func.count(TrackedPerson.id)).where(
                TrackedPerson.last_seen_at >= from_dt,
                TrackedPerson.last_seen_at <= to_dt,
            )
        )
        persons_tracked = persons_tracked_result.scalar() or 0

        # False positive rate
        false_positives_result = await self.session.execute(
            select(func.count(Alert.id)).where(
                Alert.triggered_at >= from_dt,
                Alert.triggered_at <= to_dt,
                Alert.status == AlertStatus.FALSE_POSITIVE.value,
            )
        )
        false_positives = false_positives_result.scalar() or 0
        false_positive_rate = (
            round((false_positives / total_alerts) * 100, 2) if total_alerts > 0 else 0.0
        )

        return {
            "period": {
                "from": from_dt.isoformat(),
                "to": to_dt.isoformat(),
            },
            "total_alerts": total_alerts,
            "alerts_by_priority": alerts_by_priority,
            "watchlist_matches": watchlist_matches,
            "zone_breaches": zone_breaches,
            "persons_tracked": persons_tracked,
            "false_positive_rate": false_positive_rate,
            "false_positives": false_positives,
        }

    async def get_alerts_timeline(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        granularity: str = "hour",
    ) -> List[Dict[str, Any]]:
        """
        Get alerts over time for line chart visualization.

        Args:
            from_dt: Start datetime
            to_dt: End datetime
            granularity: Time bucket granularity ('hour' or 'day')

        Returns:
            List of time buckets with alert counts by priority
        """
        if to_dt is None:
            to_dt = datetime.utcnow()
        if from_dt is None:
            from_dt = to_dt - timedelta(days=7)

        # Validate granularity
        if granularity not in ("hour", "day"):
            granularity = "hour"

        interval = "1 hour" if granularity == "hour" else "1 day"

        # Use TimescaleDB time_bucket if available, fallback to date_trunc
        try:
            query = text(
                f"""
                SELECT
                    time_bucket('{interval}', triggered_at) AS bucket,
                    priority,
                    COUNT(*) AS count
                FROM alerts
                WHERE triggered_at >= :from_dt AND triggered_at <= :to_dt
                GROUP BY bucket, priority
                ORDER BY bucket ASC
                """
            )
            result = await self.session.execute(
                query, {"from_dt": from_dt, "to_dt": to_dt}
            )
        except Exception:
            # Fallback to standard date_trunc
            trunc_unit = "hour" if granularity == "hour" else "day"
            query = text(
                f"""
                SELECT
                    date_trunc('{trunc_unit}', triggered_at) AS bucket,
                    priority,
                    COUNT(*) AS count
                FROM alerts
                WHERE triggered_at >= :from_dt AND triggered_at <= :to_dt
                GROUP BY bucket, priority
                ORDER BY bucket ASC
                """
            )
            result = await self.session.execute(
                query, {"from_dt": from_dt, "to_dt": to_dt}
            )

        rows = result.fetchall()

        # Aggregate into time-series format
        buckets: Dict[str, Dict[str, int]] = {}
        for row in rows:
            bucket_key = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
            priority = row[1]
            count = row[2]
            if bucket_key not in buckets:
                buckets[bucket_key] = {p.value: 0 for p in AlertPriority}
            buckets[bucket_key][priority] = count

        return [
            {"timestamp": ts, **counts} for ts, counts in sorted(buckets.items())
        ]

    async def get_alert_distribution(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get alert type distribution for donut chart.

        Returns:
            List of {alert_type, count, percentage} dicts
        """
        if to_dt is None:
            to_dt = datetime.utcnow()
        if from_dt is None:
            from_dt = to_dt - timedelta(days=7)

        result = await self.session.execute(
            select(Alert.alert_type, func.count(Alert.id).label("count"))
            .where(Alert.triggered_at >= from_dt, Alert.triggered_at <= to_dt)
            .group_by(Alert.alert_type)
            .order_by(func.count(Alert.id).desc())
        )
        rows = result.fetchall()

        total = sum(row[1] for row in rows)
        return [
            {
                "alert_type": row[0],
                "count": row[1],
                "percentage": round((row[1] / total) * 100, 2) if total > 0 else 0.0,
            }
            for row in rows
        ]

    async def get_zone_heatmap(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get zone activity heatmap data (zones × hours of day).

        Returns:
            List of {zone_id, hour, alert_count} dicts
        """
        if to_dt is None:
            to_dt = datetime.utcnow()
        if from_dt is None:
            from_dt = to_dt - timedelta(days=7)

        query = text(
            """
            SELECT
                zone_id,
                EXTRACT(HOUR FROM triggered_at) AS hour_of_day,
                COUNT(*) AS alert_count
            FROM alerts
            WHERE triggered_at >= :from_dt
              AND triggered_at <= :to_dt
              AND zone_id IS NOT NULL
            GROUP BY zone_id, hour_of_day
            ORDER BY zone_id, hour_of_day
            """
        )
        result = await self.session.execute(
            query, {"from_dt": from_dt, "to_dt": to_dt}
        )
        rows = result.fetchall()

        return [
            {
                "zone_id": str(row[0]),
                "hour": int(row[1]),
                "alert_count": int(row[2]),
            }
            for row in rows
        ]

    async def get_ml_performance(self) -> Dict[str, Any]:
        """
        Get ML model performance metrics.

        Returns:
            Dict with model accuracy, false positive rate trend, and latency metrics.
        """
        # Query detection events for confidence distribution
        confidence_result = await self.session.execute(
            select(
                func.avg(DetectionEvent.confidence_score).label("avg_confidence"),
                func.min(DetectionEvent.confidence_score).label("min_confidence"),
                func.max(DetectionEvent.confidence_score).label("max_confidence"),
                func.count(DetectionEvent.id).label("total_detections"),
            ).where(
                DetectionEvent.frame_timestamp >= datetime.utcnow() - timedelta(days=7)
            )
        )
        conf_row = confidence_result.fetchone()

        # Detection type breakdown
        type_result = await self.session.execute(
            select(
                DetectionEvent.detection_type,
                func.count(DetectionEvent.id).label("count"),
                func.avg(DetectionEvent.confidence_score).label("avg_confidence"),
            )
            .where(
                DetectionEvent.frame_timestamp >= datetime.utcnow() - timedelta(days=7)
            )
            .group_by(DetectionEvent.detection_type)
        )
        type_rows = type_result.fetchall()

        return {
            "period_days": 7,
            "total_detections": int(conf_row[3]) if conf_row and conf_row[3] else 0,
            "avg_confidence": float(conf_row[0]) if conf_row and conf_row[0] else 0.0,
            "min_confidence": float(conf_row[1]) if conf_row and conf_row[1] else 0.0,
            "max_confidence": float(conf_row[2]) if conf_row and conf_row[2] else 0.0,
            "by_detection_type": [
                {
                    "detection_type": row[0],
                    "count": int(row[1]),
                    "avg_confidence": float(row[2]) if row[2] else 0.0,
                }
                for row in type_rows
            ],
        }

    async def get_top_feeds(
        self,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get most active feeds by alert count.

        Returns:
            List of {feed_id, alert_count} sorted descending
        """
        if to_dt is None:
            to_dt = datetime.utcnow()
        if from_dt is None:
            from_dt = to_dt - timedelta(days=7)

        result = await self.session.execute(
            select(Alert.feed_id, func.count(Alert.id).label("alert_count"))
            .where(
                Alert.triggered_at >= from_dt,
                Alert.triggered_at <= to_dt,
                Alert.feed_id.isnot(None),
            )
            .group_by(Alert.feed_id)
            .order_by(func.count(Alert.id).desc())
            .limit(limit)
        )
        rows = result.fetchall()

        return [
            {"feed_id": str(row[0]), "alert_count": int(row[1])}
            for row in rows
        ]
