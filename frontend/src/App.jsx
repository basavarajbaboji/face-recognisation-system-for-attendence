import React, { useState } from 'react';
import Navbar from './components/Navbar';
import GateMonitor from './pages/GateMonitor';
import AttendanceReport from './pages/AttendanceReport';
import Enrollment from './pages/Enrollment';
import UnknownVisitors from './pages/UnknownVisitors';
import Calibration from './pages/Calibration';
import Settings from './pages/Settings';

export default function App() {
  const [activeTab, setActiveTab] = useState('monitor');
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  return (
    <div className="app-container">
      {/* Top Fixed Command Header */}
      <Navbar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        voiceEnabled={voiceEnabled} 
        setVoiceEnabled={setVoiceEnabled} 
      />

      {/* Main Dynamic View Area */}
      <main className="main-content">
        {activeTab === 'monitor' && <GateMonitor voiceEnabled={voiceEnabled} />}
        {activeTab === 'enrollment' && <Enrollment />}
        {activeTab === 'attendance' && <AttendanceReport />}
        {activeTab === 'settings' && <Settings />}
      </main>
    </div>
  );
}

