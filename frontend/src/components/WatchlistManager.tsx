import { useState, useEffect } from 'react';
import { UserPlus, Search, Shield, Trash2, CheckCircle, Clock } from 'lucide-react';
import axios from 'axios';

interface WatchlistEntry {
  id: string;
  name: string;
  threat_category: string;
  status: string;
  created_at: string;
}

export const WatchlistManager = () => {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [search, setSearch] = useState("");

  // Mock enrollment (Real implementation would use Axios to /api/v1/watchlist)
  useEffect(() => {
    setEntries([
      { id: '1', name: 'TARGET ALPHA', threat_category: 'TERRORIST', status: 'ACTIVE', created_at: '2024-04-20 10:00' },
      { id: '2', name: 'TARGET BRAVO', threat_category: 'CRIMINAL', status: 'PENDING', created_at: '2024-04-21 09:30' },
    ]);
  }, []);

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold glow-text">BIOMETRIC WATCHLIST</h2>
          <p className="text-xs text-slate-500 font-mono">PERSONNEL ENROLLMENT & THREAT DATABASE</p>
        </div>
        <button 
          onClick={() => setIsAdding(!isAdding)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-xs font-bold transition-all shadow-lg"
        >
          <UserPlus size={14} /> ENROLL PERSON
        </button>
      </div>

      <div className="grid grid-cols-12 gap-6 flex-1 overflow-hidden">
        {/* List View */}
        <div className="col-span-12 lg:col-span-8 tactical-border glass-panel rounded-xl overflow-hidden flex flex-col">
          <div className="p-4 border-b border-blue-500/10 flex items-center gap-4">
            <Search size={16} className="text-slate-500" />
            <input 
              type="text" 
              placeholder="SEARCH DATABASE..."
              className="bg-transparent border-none text-xs font-mono focus:outline-none w-full"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/50 sticky top-0 border-b border-blue-500/10">
                <tr>
                  <th className="p-4 text-slate-400 font-normal">NAME</th>
                  <th className="p-4 text-slate-400 font-normal">THREAT CATEGORY</th>
                  <th className="p-4 text-slate-400 font-normal">STATUS</th>
                  <th className="p-4 text-slate-400 font-normal">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-blue-500/5">
                {entries.map(entry => (
                  <tr key={entry.id} className="hover:bg-blue-500/5 transition-colors">
                    <td className="p-4 font-bold text-slate-200">{entry.name}</td>
                    <td className="p-4">
                      <span className="px-2 py-0.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-[10px]">
                        {entry.threat_category}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {entry.status === 'ACTIVE' ? <CheckCircle size={12} className="text-emerald-400" /> : <Clock size={12} className="text-amber-400" />}
                        <span className={entry.status === 'ACTIVE' ? "text-emerald-400" : "text-amber-400"}>{entry.status}</span>
                      </div>
                    </td>
                    <td className="p-4 flex gap-2">
                       <button className="p-1 text-slate-500 hover:text-red-400"><Trash2 size={14} /></button>
                       <button className="p-1 text-slate-500 hover:text-cyan-400"><Shield size={14} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Action Panel */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">
           {isAdding ? (
             <div className="tactical-border glass-panel rounded-xl p-6 animate-in slide-in-from-right-4 duration-300">
                <h3 className="text-xs font-bold text-cyan-400 tracking-widest uppercase mb-6">Enrollment Form</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] text-slate-500 font-mono mb-1">FULL NAME</label>
                    <input type="text" className="w-full bg-slate-900/50 border border-slate-800 rounded p-2 text-xs focus:border-blue-500" />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500 font-mono mb-1">THREAT CATEGORY</label>
                    <select className="w-full bg-slate-900/50 border border-slate-800 rounded p-2 text-xs focus:border-blue-500">
                      <option>CRIMINAL</option>
                      <option>TERRORIST</option>
                      <option>SUSPECT</option>
                      <option>VIP</option>
                    </select>
                  </div>
                  <div className="aspect-square border-2 border-dashed border-slate-800 rounded-xl flex flex-col items-center justify-center text-slate-500 hover:border-blue-500/50 transition-colors cursor-pointer">
                     <UserPlus size={48} className="opacity-20 mb-2" />
                     <p className="text-[10px] font-mono">UPLOAD BIOMETRIC IMAGE</p>
                  </div>
                  <button className="w-full py-3 bg-cyan-500 text-slate-900 font-bold rounded text-xs mt-4">SUBMIT FOR APPROVAL</button>
                </div>
             </div>
           ) : (
             <div className="tactical-border glass-panel rounded-xl p-6 flex flex-col items-center justify-center text-center opacity-40">
                <Shield size={64} className="text-cyan-400 mb-4" />
                <p className="text-xs font-mono tracking-widest uppercase">Select an entry or enroll new personnel to view details.</p>
             </div>
           )}
        </div>
      </div>
    </div>
  );
};
