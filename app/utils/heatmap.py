"""
Heatmap Generation Utility — Phase 20, Task 20.2

Generates zone activity heatmaps and movement heatmaps using matplotlib.
"""

import io
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def generate_zone_heatmap(
    zone_data: List[Dict],
    zone_names: Optional[Dict[str, str]] = None,
    title: str = "Zone Activity Heatmap",
    figsize: Tuple[int, int] = (14, 8),
) -> bytes:
    """
    Generate a zone × hour-of-day activity heatmap as PNG bytes.

    Args:
        zone_data: List of {zone_id, hour, alert_count} dicts from AnalyticsService
        zone_names: Optional mapping of zone_id → zone_name for labels
        title: Chart title
        figsize: Figure size (width, height) in inches

    Returns:
        PNG image bytes
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        import numpy as np

        if not zone_data:
            return _empty_chart("No zone activity data available", figsize)

        # Build zone × hour matrix
        zone_ids = sorted(set(row["zone_id"] for row in zone_data))
        hours = list(range(24))

        # Initialize matrix with zeros
        matrix = np.zeros((len(zone_ids), 24))
        zone_idx = {z: i for i, z in enumerate(zone_ids)}

        for row in zone_data:
            zi = zone_idx.get(row["zone_id"])
            h = int(row["hour"])
            if zi is not None and 0 <= h < 24:
                matrix[zi][h] = row["alert_count"]

        # Y-axis labels
        y_labels = [
            zone_names.get(z, z[:8] + "...") if zone_names else z[:12]
            for z in zone_ids
        ]

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")

        # Custom colormap: dark → red (threat-level aesthetic)
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "nsg_threat",
            ["#0d1117", "#1a2744", "#2d4a8a", "#c0392b", "#e74c3c"],
        )

        im = ax.imshow(matrix, aspect="auto", cmap=cmap, interpolation="nearest")

        # Axes
        ax.set_xticks(range(24))
        ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45, ha="right",
                           fontsize=8, color="#8b949e")
        ax.set_yticks(range(len(zone_ids)))
        ax.set_yticklabels(y_labels, fontsize=9, color="#c9d1d9")

        # Labels
        ax.set_xlabel("Hour of Day (UTC)", color="#8b949e", fontsize=10)
        ax.set_ylabel("Security Zone", color="#8b949e", fontsize=10)
        ax.set_title(title, color="#f0f6fc", fontsize=13, fontweight="bold", pad=15)

        # Colorbar
        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("Alert Count", color="#8b949e", fontsize=9)
        cbar.ax.yaxis.set_tick_params(color="#8b949e")
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#8b949e")

        # Annotate cells with counts > 0
        for i in range(len(zone_ids)):
            for j in range(24):
                val = int(matrix[i][j])
                if val > 0:
                    ax.text(j, i, str(val), ha="center", va="center",
                            fontsize=7, color="white", fontweight="bold")

        # Grid
        ax.set_xticks(np.arange(-0.5, 24, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(zone_ids), 1), minor=True)
        ax.grid(which="minor", color="#21262d", linewidth=0.5)
        ax.tick_params(which="minor", bottom=False, left=False)

        # Spine colors
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except ImportError:
        logger.warning("matplotlib not installed, returning placeholder heatmap")
        return _placeholder_png()
    except Exception as e:
        logger.error("Heatmap generation failed: %s", e)
        return _placeholder_png()


def generate_movement_heatmap(
    trajectory_points: List[Dict],
    width: int = 1920,
    height: int = 1080,
    title: str = "Person Movement Heatmap",
    figsize: Tuple[int, int] = (12, 7),
) -> bytes:
    """
    Generate a 2D movement density heatmap from trajectory points.

    Args:
        trajectory_points: List of {x, y, confidence} dicts (x,y as 0.0-1.0 fractions)
        width: Frame width for coordinate scaling
        height: Frame height for coordinate scaling
        title: Chart title
        figsize: Figure size in inches

    Returns:
        PNG image bytes
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        if not trajectory_points:
            return _empty_chart("No movement data available", figsize)

        xs = [p.get("x", 0.5) * width for p in trajectory_points]
        ys = [p.get("y", 0.5) * height for p in trajectory_points]

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")

        # 2D histogram density
        h, xedges, yedges = np.histogram2d(xs, ys, bins=40)
        h = h.T  # Transpose for correct orientation

        import matplotlib.colors as mcolors
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "movement",
            ["#0d1117", "#0d3b6e", "#1a7abf", "#f39c12", "#e74c3c"],
        )

        ax.imshow(
            h,
            origin="lower",
            extent=[0, width, 0, height],
            cmap=cmap,
            aspect="auto",
            interpolation="gaussian",
        )

        # Overlay trajectory path
        ax.plot(xs, ys, color="#00f2ff", linewidth=0.8, alpha=0.4, zorder=2)
        ax.scatter(xs[0], ys[0], color="#00ff88", s=60, zorder=3, label="Start")
        ax.scatter(xs[-1], ys[-1], color="#ff4444", s=60, zorder=3, label="End")

        ax.set_xlim(0, width)
        ax.set_ylim(0, height)
        ax.set_title(title, color="#f0f6fc", fontsize=13, fontweight="bold")
        ax.set_xlabel("X Position (px)", color="#8b949e")
        ax.set_ylabel("Y Position (px)", color="#8b949e")
        ax.tick_params(colors="#8b949e")
        ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9")

        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except ImportError:
        logger.warning("matplotlib not installed, returning placeholder")
        return _placeholder_png()
    except Exception as e:
        logger.error("Movement heatmap generation failed: %s", e)
        return _placeholder_png()


def _empty_chart(message: str, figsize: Tuple[int, int]) -> bytes:
    """Generate a simple 'no data' chart."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")
        ax.text(0.5, 0.5, message, ha="center", va="center",
                color="#8b949e", fontsize=14, transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception:
        return _placeholder_png()


def _placeholder_png() -> bytes:
    """Minimal valid 1×1 transparent PNG as fallback."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
