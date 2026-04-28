import { useAlerts } from '../hooks/useAlerts';
import type { Alert } from '../types';
import { AlertTriangle, ChevronRight, Clock, MapPin } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const AlertCard = ({ alert }: { alert: Alert }) => (
  <div className={cn(
    "p-3 rounded-lg border transition-all duration-200",
    alert.priority === 'P1_CRITICAL' 
      ? "bg-red-500/10 border-red-500/30 animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.1)]" 
      : "bg-slate-800/50 border-slate-700/50 hover:border-blue-500/30"
  )}>
    <div className="flex justify-between items-center mb-2">
      <span className={cn(
        "text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-tighter",
        alert.priority === 'P1_CRITICAL' ? "bg-red-500 text-white" :
        alert.priority === 'P2_HIGH' ? "bg-amber-500 text-slate-950" : "bg-slate-700 text-slate-300"
      )}>
        {alert.priority.replace('_', ' ')}
      </span>
      <div className="flex items-center gap-1 text-[10px] text-slate-500 font-mono">
        <Clock size={10} />
        {new Date(alert.triggered_at).toLocaleTimeString()}
      </div>
    </div>
    
    <h4 className="text-xs font-bold text-slate-100 uppercase mb-1">{alert.type.replace('_', ' ')}</h4>
    
    <div className="flex items-center gap-2 mt-2 text-[10px] text-slate-400 font-mono">
      <MapPin size={10} className="text-cyan-400" />
      <span>DEVICE: {alert.feed_id.slice(0, 8)}</span>
      <div className="ml-auto flex items-center gap-1 text-cyan-400 hover:underline cursor-pointer">
        VIEW <ChevronRight size={10} />
      </div>
    </div>
  </div>
);

export const AlertInbox = () => {
  const { alerts, isConnected } = useAlerts();

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-blue-500/10">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-bold text-cyan-400 tracking-wider">REAL-TIME INBOX</h3>
          <div className={cn(
            "w-1.5 h-1.5 rounded-full",
            isConnected ? "bg-emerald-500" : "bg-red-500"
          )} />
        </div>
        <span className="text-[10px] font-mono text-slate-500">{alerts.length} ACTIVE</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin">
        {alerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center opacity-20 text-center">
            <AlertTriangle size={32} className="mb-2" />
            <p className="text-[10px] font-mono tracking-widest">SCANNING FOR THREATS...</p>
          </div>
        ) : (
          alerts.map(alert => <AlertCard key={alert.id} alert={alert} />)
        )}
      </div>
    </div>
  );
};
