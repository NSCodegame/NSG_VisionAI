import { useState, useEffect, useRef } from 'react';
import { Maximize, Minimize, Settings, Play, Pause, AlertTriangle } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface VideoPlayerProps {
  feedId: string;
  feedName: string;
  status: 'active' | 'offline' | 'alert';
  isMuted?: boolean;
}

export const VideoPlayer = ({ feedId, feedName, status, isMuted = true }: VideoPlayerProps) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isPlaying, setIsPlaying] = useState(true);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Simulated AI Overlay Logic
  useEffect(() => {
    if (!isPlaying || !canvasRef.current) return;
    
    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    let frameId: number;
    const draw = () => {
      ctx.clearRect(0, 0, canvasRef.current!.width, canvasRef.current!.height);
      
      // Simulate Bounding Box for Person Detection
      if (Math.random() > 0.3) {
        ctx.strokeStyle = '#00f2ff'; // Tactical Cyan
        ctx.lineWidth = 2;
        ctx.strokeRect(50, 60, 80, 120);
        
        ctx.fillStyle = '#00f2ff';
        ctx.font = '10px monospace';
        ctx.fillText('TARGET: PERSON (98%)', 50, 55);
      }

      frameId = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(frameId);
  }, [isPlaying]);

  return (
    <div 
      className={cn(
        "relative rounded-lg overflow-hidden glass-panel group h-full",
        status === 'alert' ? "border-red-500/50 shadow-[0_0_20px_rgba(244,63,94,0.2)]" : "border-blue-500/10"
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Video Content Placeholder */}
      <div className="absolute inset-0 bg-slate-950 flex items-center justify-center">
        {status === 'offline' ? (
          <div className="text-center text-slate-600">
             <AlertTriangle className="w-12 h-12 mx-auto mb-2 opacity-20" />
             <p className="text-xs font-mono">FEED DISCONNECTED</p>
          </div>
        ) : (
          <div className="w-full h-full bg-[url('https://images.unsplash.com/photo-1541888941297-dc59633c82ee?q=80&w=2070&auto=format&fit=crop')] bg-cover bg-center opacity-40 mix-blend-screen" />
        )}
      </div>

      {/* AI Overlays (Canvas Layer) */}
      <canvas 
        ref={canvasRef}
        width={400} 
        height={300}
        className="absolute inset-0 w-full h-full pointer-events-none"
      />

      {/* UI Overlays */}
      <div className="absolute top-0 left-0 p-3 w-full flex justify-between items-start bg-gradient-to-b from-black/60 to-transparent">
        <div>
          <h4 className="text-[10px] font-bold text-slate-100 tracking-widest uppercase">{feedName}</h4>
          <p className="text-[8px] text-slate-400 font-mono tracking-tighter uppercase">CAM: {feedId.slice(0,8)}</p>
        </div>
        <div className={cn(
          "w-2 h-2 rounded-full",
          status === 'active' ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : 
          status === 'alert' ? "bg-red-500 alert-pulse" : "bg-slate-600"
        )} />
      </div>

      {/* Hover Controls */}
      <div className={cn(
        "absolute bottom-0 left-0 w-full p-2 flex justify-between items-center bg-gradient-to-t from-black/80 to-transparent transition-opacity duration-200",
        isHovered ? "opacity-100" : "opacity-0"
      )}>
        <div className="flex gap-2">
          <button onClick={() => setIsPlaying(!isPlaying)} className="p-1 hover:text-cyan-400 transition-colors">
            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button className="p-1 hover:text-cyan-400 transition-colors"><Settings size={14} /></button>
        </div>
        <div className="flex gap-2">
          <button className="p-1 hover:text-cyan-400 transition-colors"><Maximize size={14} /></button>
        </div>
      </div>

      {/* Sensor Data Overlay (Tactical look) */}
      <div className="absolute top-1/2 left-3 -translate-y-1/2 flex flex-col gap-1 pointer-events-none">
        <div className="h-12 w-[1px] bg-cyan-500/20" />
        <div className="text-[8px] text-cyan-400/40 font-mono rotate-90 origin-left ml-2 whitespace-nowrap">LAT: 28.5355 N</div>
        <div className="h-12 w-[1px] bg-cyan-500/20" />
      </div>
    </div>
  );
};
