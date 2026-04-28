import { VideoPlayer } from './VideoPlayer';

interface Feed {
  id: string;
  name: string;
  status: 'active' | 'offline' | 'alert';
}

const MOCK_FEEDS: Feed[] = [
  { id: 'cam-01', name: 'MAIN GATE - ENTRANCE', status: 'active' },
  { id: 'cam-02', name: 'PERIMETER NORTH - ZONE 3', status: 'alert' },
  { id: 'cam-03', name: 'PARKING AREA B', status: 'active' },
  { id: 'cam-04', name: 'SERVER ROOM - INTERNAL', status: 'offline' },
  { id: 'cam-05', name: 'CORRIDOR 4 - LEVEL 2', status: 'active' },
  { id: 'cam-06', name: 'LOBBY - RECEPTION', status: 'alert' },
];

export const VideoGrid = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 h-full p-1 overflow-y-auto">
      {MOCK_FEEDS.map((feed) => (
        <div key={feed.id} className="aspect-video">
          <VideoPlayer 
            feedId={feed.id}
            feedName={feed.name}
            status={feed.status}
          />
        </div>
      ))}
    </div>
  );
};
