/**
 * VideoGrid — Real feed grid using live MJPEG streams
 *
 * Reads feeds from the Zustand store (populated by DashboardPage).
 * Each card connects to /api/v1/streams/{feedId}/mjpeg for live video.
 */

import { VideoPlayer } from "./VideoPlayer";
import { useFeedStore } from "../stores";
import { Monitor } from "lucide-react";

export const VideoGrid = () => {
  const { feeds } = useFeedStore();

  if (feeds.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-700">
        <Monitor size={40} />
        <p className="text-xs font-mono tracking-widest uppercase">No feeds configured</p>
        <p className="text-[10px] text-slate-600">Add feeds via the FEEDS tab</p>
      </div>
    );
  }

  // Grid layout based on feed count
  const gridCols =
    feeds.length === 1 ? "grid-cols-1" :
    feeds.length <= 4 ? "grid-cols-2" :
    "grid-cols-3";

  return (
    <div className={`grid ${gridCols} gap-3 h-full overflow-y-auto`}>
      {feeds.map((feed) => (
        <div key={feed.id} className="aspect-video min-h-[140px]">
          <VideoPlayer
            feedId={feed.id}
            feedName={feed.name}
            status={feed.status}
            aiEnabled={feed.ai_processing_enabled ?? false}
            location={feed.location_name}
            resolution={feed.resolution}
            fps={feed.fps}
          />
        </div>
      ))}
    </div>
  );
};
