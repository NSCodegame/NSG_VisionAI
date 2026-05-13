import { useState, useEffect } from 'react';
import { UserPlus, Search, Shield, Trash2, CheckCircle, Clock, AlertTriangle, Eye } from 'lucide-react';
import { WATCHLIST_ENTRIES } from '../data/seedData';

interface WatchlistEntry {
  id: string;
  name: string;
  alias?: string;
  threat_category: string;
  status: string;
  last_seen_location?: string;
  last_seen_at?: string;
  confidence_score?: number;
  associated_vehicle?: string;
  threat_notes?: string;
  source_agency?: string;
  created_at: string;
}

const THREAT_COLORS: Record<string, string> = {
  KNOWN_TERRORIST:  "text-red-400 bg-red-900/20 border-red-500/30",
  ORGANIZED_CRIME:  "text-orange-400 bg-orange-900/20 border-orange-500/30",
  WEAPON_SMUGGLING: "text-yellow-400 bg-yellow-900/20 border-yellow-500/30",
  CYBERCRIME:       "text-purple-400 bg-purple-900/20 border-purple-500/30",
  SUSPECT:          "text-blue-400 bg-blue-900/20 border-blue-500/30",
};

export const WatchlistManager = () => {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [selected, setSelected] = useState<WatchlistEntry | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    // Try real API first, fall back to seed data
    import('axios').then(({ default: axios }) => {
      const token = localStorage.getItem("access_token");
      axios.get('/api/v1/watchlist', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }).then((res) => {
        const data = res.data?.entries ?? res.data ?? [];
        if (Array.isArray(data) && data.length > 0) {
          setEntries(data);
        } else {
          setEntries(WATCHLIST_ENTRIES as WatchlistEntry[]);
        }
      }).catch(() => {
        setEntries(WATCHLIST_ENTRIES as WatchlistEntry[]);
      });
    });
  }, []);

  const filtered = entries.filter((e) =>
    search === "" ||
    e.name.toLowerCase().includes(search.toLowerCase()) ||
    (e.alias ?? "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">BIOMETRIC WATCHLIST</h2>
          <p className="text-xs text-slate-500 font-mono">PERSONNEL ENROLLMENT &amp; THREAT DATABASE</p>
        </div>
        <button
          onClick={() => setIsAdding(!isAdding)}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 border border-cyan-500/40 hover:bg-cyan-500/30 rounded text-xs font-bold text-cyan-400 transition-all"
        >
          <UserPlus size={14} /> ENROLL PERSON
        </button>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden min-h-0">
        {/* List */}
        <div className="flex-1 bg-slate-900/60 border border-slate-700 rounded-xl overflow-hidden flex flex-col">
          {/* Search */}
          <div className="p-3 border-b border-blue-500/10 flex items-center gap-3">
            <Search size={14} className="text-slate-500 shrink-0" />
            <input
              type="text"
              placeholder="SEARCH DATABASE..."
              className="bg-transparent border-none text-xs font-mono focus:outline-none w-full text-slate-300 placeholder-slate-600"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <span className="text-[10px] text-slate-600 font-mono shrink-0">{filtered.length} ENTRIES</span>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/80 sticky top-0 border-b border-blue-500/10">
                <tr>
                  {["NAME", "THREAT CATEGORY", "STATUS", "LAST SEEN", "ACTIONS"].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-[10px] text-slate-500 font-bold uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-blue-500/5">
                {filtered.map((entry) => {
                  const threatColor = THREAT_COLORS[entry.threat_category] ?? "text-slate-400 bg-slate-800 border-slate-600";
                  return (
                    <tr
                      key={entry.id}
                      onClick={() => setSelected(entry)}
                      className={`hover:bg-blue-500/5 transition-colors cursor-pointer ${selected?.id === entry.id ? "bg-blue-500/10" : ""}`}
                    >
                      <td className="px-4 py-3">
                        <p className="font-bold text-slate-200">{entry.name}</p>
                        {entry.alias && <p className="text-[10px] text-slate-500 mt-0.5">aka {entry.alias}</p>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 border rounded-full text-[10px] font-bold ${threatColor}`}>
                          {entry.threat_category.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          {entry.status === "ACTIVE"
                            ? <CheckCircle size={11} className="text-emerald-400" />
                            : <Clock size={11} className="text-amber-400" />}
                          <span className={entry.status === "ACTIVE" ? "text-emerald-400" : "text-amber-400"}>
                            {entry.status}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-500 text-[10px]">
                        <p>{entry.last_seen_location ?? "—"}</p>
                        {entry.last_seen_at && (
                          <p className="text-slate-600 mt-0.5">
                            {new Date(entry.last_seen_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1.5">
                          <button
                            onClick={(e) => { e.stopPropagation(); setSelected(entry); }}
                            className="p-1 text-slate-500 hover:text-cyan-400 transition-colors"
                            title="View details"
                          >
                            <Eye size={13} />
                          </button>
                          <button className="p-1 text-slate-500 hover:text-red-400 transition-colors" title="Remove">
                            <Trash2 size={13} />
                          </button>
                          <button className="p-1 text-slate-500 hover:text-cyan-400 transition-colors" title="Intel">
                            <Shield size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Detail / Enroll panel */}
        <div className="w-80 shrink-0 flex flex-col gap-3">
          {isAdding ? (
            <div className="bg-slate-900/60 border border-slate-700 rounded-xl p-5 flex flex-col gap-4">
              <h3 className="text-xs font-bold text-cyan-400 tracking-widest uppercase">Enrollment Form</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-[10px] text-slate-500 font-mono mb-1 uppercase">Full Name</label>
                  <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/50" />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500 font-mono mb-1 uppercase">Threat Category</label>
                  <select className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500/50">
                    {["KNOWN_TERRORIST","ORGANIZED_CRIME","WEAPON_SMUGGLING","CYBERCRIME","SUSPECT"].map((c) => (
                      <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
                <div className="aspect-square border-2 border-dashed border-slate-700 rounded-xl flex flex-col items-center justify-center text-slate-500 hover:border-cyan-500/40 transition-colors cursor-pointer">
                  <UserPlus size={36} className="opacity-20 mb-2" />
                  <p className="text-[10px] font-mono">UPLOAD BIOMETRIC IMAGE</p>
                </div>
                <button className="w-full py-2.5 bg-cyan-500 text-slate-900 font-bold rounded text-xs">SUBMIT FOR APPROVAL</button>
                <button onClick={() => setIsAdding(false)} className="w-full py-2 border border-slate-700 text-slate-400 rounded text-xs hover:border-slate-500">Cancel</button>
              </div>
            </div>
          ) : selected ? (
            <div className="bg-slate-900/60 border border-slate-700 rounded-xl p-5 flex flex-col gap-3 overflow-y-auto">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white">{selected.name}</h3>
                  {selected.alias && <p className="text-[10px] text-slate-500 font-mono mt-0.5">aka {selected.alias}</p>}
                </div>
                <span className={`px-2 py-0.5 border rounded-full text-[10px] font-bold ${THREAT_COLORS[selected.threat_category] ?? ""}`}>
                  {selected.threat_category.replace(/_/g, " ")}
                </span>
              </div>

              <div className="space-y-2 text-[11px] font-mono">
                {[
                  ["Status", selected.status],
                  ["Confidence", selected.confidence_score ? `${(selected.confidence_score * 100).toFixed(0)}%` : "—"],
                  ["Last Seen", selected.last_seen_location ?? "—"],
                  ["Vehicle", selected.associated_vehicle ?? "—"],
                  ["Source", selected.source_agency ?? "—"],
                  ["Enrolled", new Date(selected.created_at).toLocaleDateString("en-IN")],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-2">
                    <span className="text-slate-500 uppercase shrink-0">{label}</span>
                    <span className="text-slate-300 text-right">{value}</span>
                  </div>
                ))}
              </div>

              {selected.threat_notes && (
                <div className="bg-red-900/10 border border-red-500/20 rounded-lg p-3">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <AlertTriangle size={11} className="text-red-400" />
                    <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider">Threat Notes</span>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-relaxed">{selected.threat_notes}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-slate-900/60 border border-slate-700 rounded-xl p-6 flex flex-col items-center justify-center text-center opacity-40 flex-1">
              <Shield size={48} className="text-cyan-400 mb-3" />
              <p className="text-xs font-mono tracking-widest uppercase text-slate-400">
                Select an entry or enroll new personnel to view details.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

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
