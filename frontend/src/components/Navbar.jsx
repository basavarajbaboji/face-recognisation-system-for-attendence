import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  Users, 
  ClipboardCheck, 
  UserX, 
  Sliders, 
  Activity, 
  Settings as SettingsIcon,
  ShieldCheck,
  Volume2,
  VolumeX,
  Presentation
} from 'lucide-react';
import { API_BASE } from '../config';

export default function Navbar({ activeTab, setActiveTab, voiceEnabled, setVoiceEnabled, isOnline = true }) {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'monitor', label: 'Live Surveillance', icon: Camera },
    { id: 'enrollment', label: 'People & Enrollment', icon: Users },
    { id: 'attendance', label: 'Attendance & Logs', icon: ClipboardCheck },
    { id: 'settings', label: 'CCTV & Settings', icon: SettingsIcon }
  ];

  return (
    <header className="navbar">
      <div className="brand-section">
        <div className="brand-logo-badge">
          <ShieldCheck size={24} color="#041322" />
        </div>
        <div>
          <h1 className="brand-title">CAMPUS SENTINEL AI</h1>
          <div className="brand-subtitle">
            <span className="font-mono">{timeStr}</span>
            <span>•</span>
            <span>Main Gate Surveillance</span>
          </div>
        </div>
      </div>

      <nav className="nav-links">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="nav-status">
        <a 
          href={`${API_BASE}/presentation`} 
          target="_blank" 
          rel="noreferrer"
          className="btn btn-secondary"
          style={{ padding: '6px 12px', fontSize: '0.78rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
          title="Open Tech Expo Presentation Deck (4 Slides)"
        >
          <Presentation size={16} color="#38bdf8" />
          <span>Expo PPT</span>
        </a>

        <button 
          className="btn btn-secondary" 
          style={{ padding: '6px 12px', fontSize: '0.78rem' }}
          onClick={() => setVoiceEnabled(!voiceEnabled)}
          title={voiceEnabled ? "Voice Greetings Enabled" : "Voice Greetings Muted"}
        >
          {voiceEnabled ? <Volume2 size={16} color="#38bdf8" /> : <VolumeX size={16} color="#64748b" />}
          <span>{voiceEnabled ? "Voice On" : "Muted"}</span>
        </button>

        <div className="status-pill">
          <span className="pulse-dot"></span>
          <span>{isOnline ? "LIVE SURVEILLANCE" : "OFFLINE"}</span>
        </div>
      </div>
    </header>
  );
}
