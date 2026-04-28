import { 
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, PieChart, Pie
} from 'recharts';
import { Activity, Shield, Users, AlertTriangle } from 'lucide-react';

const TREND_DATA = [
  { time: '12:00', threats: 2, detections: 45 },
  { time: '12:10', threats: 5, detections: 82 },
  { time: '12:20', threats: 3, detections: 61 },
  { time: '12:30', threats: 8, detections: 95 },
  { time: '12:40', threats: 12, detections: 140 },
  { time: '12:50', threats: 7, detections: 110 },
  { time: '13:00', threats: 4, detections: 85 },
];

const CLASSIFICATION_DATA = [
  { name: 'PERSON', value: 450, color: '#00f2ff' },
  { name: 'VEHICLE', value: 300, color: '#3b82f6' },
  { name: 'WEAPON', value: 12, color: '#f43f5e' },
  { name: 'ANOMALY', value: 45, color: '#f59e0b' },
];

export const AnalyticsDashboard = () => {
  return (
    <div className="flex flex-col gap-6 h-full overflow-y-auto pr-2">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'TOTAL TARGETS', value: '812', icon: Users, color: 'text-cyan-400' },
          { label: 'ACTIVE ALERTS', value: '04', icon: AlertTriangle, color: 'text-red-400' },
          { label: 'SECURE NODES', value: '12/12', icon: Shield, color: 'text-emerald-400' },
          { label: 'SYS THROUGHPUT', value: '2.4 GB/s', icon: Activity, color: 'text-blue-400' },
        ].map((stat, i) => (
          <div key={i} className="glass-panel p-4 rounded-xl border border-blue-500/10 flex items-center justify-between">
            <div>
              <p className="text-[10px] font-mono text-slate-500 uppercase tracking-tighter">{stat.label}</p>
              <p className={stat.color + " text-xl font-bold mt-1"}>{stat.value}</p>
            </div>
            <stat.icon className={stat.color + " w-8 h-8 opacity-20"} />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Threat Intensity Chart */}
        <div className="col-span-12 lg:col-span-8 tactical-border glass-panel rounded-xl p-6 h-80">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xs font-bold text-cyan-400 tracking-widest uppercase">Threat Intensity (Hourly)</h3>
            <div className="flex gap-4 text-[10px] font-mono">
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-400" /> THREATS</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> DETECTIONS</div>
            </div>
          </div>
          
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={TREND_DATA}>
              <defs>
                <linearGradient id="colorThreats" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="time" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <YAxis stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
                itemStyle={{ color: '#00f2ff' }}
              />
              <Area type="monotone" dataKey="threats" stroke="#f43f5e" fillOpacity={1} fill="url(#colorThreats)" strokeWidth={2} />
              <Area type="monotone" dataKey="detections" stroke="#3b82f6" fill="transparent" strokeWidth={1} strokeDasharray="5 5" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Classification Breakdown */}
        <div className="col-span-12 lg:col-span-4 tactical-border glass-panel rounded-xl p-6 h-80">
          <h3 className="text-xs font-bold text-cyan-400 tracking-widest uppercase mb-6">Target Classification</h3>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={CLASSIFICATION_DATA}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {CLASSIFICATION_DATA.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip 
                 contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '10px' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 gap-2 mt-4">
             {CLASSIFICATION_DATA.map((d, i) => (
               <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-slate-500">{d.name}</span>
                  <span className="ml-auto text-slate-300 font-bold">{d.value}</span>
               </div>
             ))}
          </div>
        </div>
      </div>
    </div>
  );
};
