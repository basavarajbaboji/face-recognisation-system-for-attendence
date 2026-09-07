import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  Camera, 
  Sliders, 
  Shield, 
  Save, 
  CheckCircle2, 
  Plus, 
  Trash2, 
  Video, 
  RefreshCw 
} from 'lucide-react';

export default function Settings() {
  const [cameraList, setCameraList] = useState([]);
  const [newCamName, setNewCamName] = useState('');
  const [newCamSource, setNewCamSource] = useState('1');
  const [camLoading, setCamLoading] = useState(false);

  const [similarityThreshold, setSimilarityThreshold] = useState(0.60);
  const [minQuality, setMinQuality] = useState(25.0);
  const [cooldownMinutes, setCooldownMinutes] = useState(10);
  const [lateTime, setLateTime] = useState('09:15');
  
  const [loading, setLoading] = useState(false);
  const [savedMsg, setSavedMsg] = useState(false);

  const [hardwareCams, setHardwareCams] = useState([]);
  const [scanningHw, setScanningHw] = useState(false);

  const fetchCameras = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/camera/list');
      if (res.ok) {
        setCameraList(await res.json());
      }
    } catch (e) {
      console.error("Error loading cameras:", e);
    }
  };

  const scanHardware = async () => {
    setScanningHw(true);
    try {
      const res = await fetch('http://localhost:8000/api/camera/detect');
      if (res.ok) {
        setHardwareCams(await res.json());
      }
    } catch (e) {
      alert("Error detecting cameras: " + e.message);
    } finally {
      setScanningHw(false);
    }
  };

  const handleAttachCamera = async (cam) => {
    try {
      const res = await fetch('http://localhost:8000/api/camera/attach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: cam.id || cam.attached_cam_id || `cam_${cam.source}`,
          name: cam.name,
          source: cam.source
        })
      });
      if (res.ok) {
        await fetchCameras();
        await scanHardware();
      } else {
        alert("Failed to attach camera to process.");
      }
    } catch (e) {
      alert("Error attaching camera: " + e.message);
    }
  };

  const handleDetachCamera = async (camId) => {
    try {
      const res = await fetch('http://localhost:8000/api/camera/detach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: camId })
      });
      if (res.ok) {
        await fetchCameras();
        await scanHardware();
      } else {
        alert("Failed to detach camera from process.");
      }
    } catch (e) {
      alert("Error detaching camera: " + e.message);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/camera/settings');
      if (res.ok) {
        const data = await res.json();
        if (data.similarity_threshold !== undefined) setSimilarityThreshold(parseFloat(data.similarity_threshold));
        if (data.min_quality_score !== undefined) setMinQuality(parseFloat(data.min_quality_score));
        if (data.attendance_cooldown_minutes !== undefined) setCooldownMinutes(parseInt(data.attendance_cooldown_minutes));
        if (data.late_time !== undefined) setLateTime(data.late_time);
      }
    } catch (e) {
      console.error("Error loading settings:", e);
    }
  };

  useEffect(() => {
    fetchCameras();
    scanHardware();
    fetchSettings();
  }, []);

  const handleAddCamera = async (e) => {
    e.preventDefault();
    if (!newCamName.trim()) return;
    setCamLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/camera/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newCamName.trim(),
          source: newCamSource.trim()
        })
      });
      if (res.ok) {
        await fetchCameras();
        await scanHardware();
        setNewCamName('');
        setNewCamSource('1');
      } else {
        alert("Could not add camera.");
      }
    } catch (e) {
      alert("Error adding camera: " + e.message);
    } finally {
      setCamLoading(false);
    }
  };

  const handleDeleteCamera = async (camId) => {
    if (!confirm(`Are you sure you want to remove this camera permanently?`)) return;
    try {
      const res = await fetch(`http://localhost:8000/api/camera/${camId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        await fetchCameras();
        await scanHardware();
      }
    } catch (e) {
      alert("Error removing camera: " + e.message);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/camera/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          similarity_threshold: parseFloat(similarityThreshold),
          min_quality_score: parseFloat(minQuality),
          attendance_cooldown_minutes: parseInt(cooldownMinutes),
          late_time: lateTime
        })
      });
      if (res.ok) {
        setSavedMsg(true);
        setTimeout(() => setSavedMsg(false), 3000);
      }
    } catch (e) {
      alert("Error saving settings: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '860px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '22px' }}>
      
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <SettingsIcon size={24} color="#38bdf8" />
          <div>
            <h2 className="font-heading" style={{ fontSize: '1.25rem', fontWeight: 600 }}>CCTV Camera & Gate Setup</h2>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Real hardware webcam detection, click-to-use / click-to-detach process controls, and AI recognition thresholds.</p>
          </div>
        </div>

        {savedMsg && (
          <div className="glass-panel" style={{ padding: '12px 18px', background: 'rgba(16, 185, 129, 0.15)', borderLeft: '4px solid #10b981', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
            <CheckCircle2 size={18} color="#10b981" />
            <span style={{ fontSize: '0.88rem', color: '#10b981', fontWeight: 500 }}>Settings saved and live pipeline reloaded!</span>
          </div>
        )}

        {/* Section 1: Real Hardware Camera Detection & Process Control */}
        <div style={{ marginBottom: '28px', background: 'rgba(56, 189, 248, 0.03)', padding: '18px', borderRadius: '10px', border: '1px solid rgba(56, 189, 248, 0.15)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
            <div>
              <h3 style={{ fontSize: '0.98rem', fontWeight: 600, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Camera size={18} /> Real Hardware Camera Detection
              </h3>
              <p style={{ fontSize: '0.76rem', color: '#94a3b8' }}>
                Scans physical webcams and USB devices connected to this machine. Click "Use" to attach to the live AI pipeline or "Detach" to release the hardware handle (0% CPU).
              </p>
            </div>

            <button 
              className="btn btn-secondary" 
              onClick={scanHardware} 
              disabled={scanningHw}
              style={{ fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={13} className={scanningHw ? "animate-spin" : ""} />
              <span>{scanningHw ? "Scanning USB..." : "Detect Connected Cameras"}</span>
            </button>
          </div>

          {/* Hardware List Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px', marginBottom: '10px' }}>
            {hardwareCams.length > 0 ? (
              hardwareCams.map((hw) => (
                <div 
                  key={hw.source} 
                  className="glass-panel" 
                  style={{ 
                    padding: '12px 14px', 
                    background: hw.is_attached ? 'rgba(16, 185, 129, 0.06)' : 'rgba(255, 255, 255, 0.02)',
                    border: hw.is_attached ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex', 
                    flexDirection: 'column', 
                    gap: '8px' 
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: hw.is_attached ? '#10b981' : '#64748b' }}></div>
                      <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>{hw.name}</span>
                    </div>
                    <span className={`badge ${hw.is_attached ? 'badge-confirmed' : 'badge-candidate'}`} style={{ fontSize: '0.68rem' }}>
                      {hw.is_attached ? `In Use (${hw.fps || 30} FPS)` : 'Available'}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }} className="font-mono">
                    Hardware Source: Device Index {hw.source} • {hw.resolution}
                  </div>

                  <div style={{ marginTop: '4px' }}>
                    {hw.is_attached ? (
                      <button 
                        className="btn btn-secondary" 
                        style={{ width: '100%', padding: '5px 8px', fontSize: '0.76rem', color: '#f43f5e', borderColor: 'rgba(244, 63, 94, 0.35)' }}
                        onClick={() => handleDetachCamera(hw.attached_cam_id || `cam_${hw.source}`)}
                      >
                        ⏹ Click to Detach from Process
                      </button>
                    ) : (
                      <button 
                        className="btn btn-primary" 
                        style={{ width: '100%', padding: '5px 8px', fontSize: '0.76rem' }}
                        onClick={() => handleAttachCamera({ id: `cam_${hw.source}`, name: `Webcam (Device ${hw.source})`, source: hw.source })}
                      >
                        ▶ Click to Use (Attach to Process)
                      </button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ textAlign: 'center', padding: '16px', color: '#64748b', fontSize: '0.8rem', gridColumn: '1 / -1' }}>
                Click "Detect Connected Cameras" to query physical camera devices on this machine.
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Configured Streams & CCTV Feeds */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#38bdf8', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Video size={16} /> Configured Camera Sources ({cameraList.length})
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
            {cameraList.map((cam) => (
              <div 
                key={cam.id} 
                className="glass-panel" 
                style={{ 
                  padding: '12px 16px', 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  background: cam.is_attached ? 'rgba(255, 255, 255, 0.03)' : 'rgba(255, 255, 255, 0.01)',
                  border: cam.is_attached ? '1px solid rgba(56, 189, 248, 0.2)' : '1px solid rgba(255, 255, 255, 0.05)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: cam.is_attached ? '#10b981' : '#64748b' }}></div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#f8fafc' }}>{cam.name}</div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }} className="font-mono">
                      Source: {cam.source} • {cam.is_attached ? `${cam.fps || 0} FPS` : 'Detached / 0% CPU'}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {cam.is_attached ? (
                    <button 
                      className="btn btn-secondary"
                      style={{ padding: '4px 10px', fontSize: '0.75rem', color: '#f43f5e', borderColor: 'rgba(244, 63, 94, 0.3)' }}
                      onClick={() => handleDetachCamera(cam.id)}
                      title="Detach from process and release camera handle"
                    >
                      Detach
                    </button>
                  ) : (
                    <button 
                      className="btn btn-primary"
                      style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      onClick={() => handleAttachCamera(cam)}
                      title="Attach to process and start AI face recognition"
                    >
                      Attach (Use)
                    </button>
                  )}

                  {cameraList.length > 1 && (
                    <button 
                      className="btn btn-secondary" 
                      style={{ padding: '4px 8px', color: '#f43f5e', borderColor: 'rgba(244, 63, 94, 0.3)' }}
                      onClick={() => handleDeleteCamera(cam.id)}
                      title="Delete Camera Configuration"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Add New Camera Inline Form */}
          <form onSubmit={handleAddCamera} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', padding: '14px', background: 'rgba(56, 189, 248, 0.04)', borderRadius: '8px', border: '1px dashed rgba(56, 189, 248, 0.25)' }}>
            <input 
              type="text" 
              className="form-input" 
              placeholder="Camera / Gate Name (e.g. South Gate)" 
              value={newCamName}
              onChange={(e) => setNewCamName(e.target.value)}
              style={{ flex: '1 1 200px' }}
              required
            />
            <input 
              type="text" 
              className="form-input font-mono" 
              placeholder="Source (e.g. 0, 1, or rtsp://...)" 
              value={newCamSource}
              onChange={(e) => setNewCamSource(e.target.value)}
              style={{ flex: '1 1 180px' }}
              required
            />
            <button 
              type="submit" 
              className="btn btn-primary" 
              disabled={camLoading}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
            >
              {camLoading ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
              <span>Add & Attach Camera</span>
            </button>
          </form>
        </div>

        {/* Section 2: AI Recognition Parameters */}
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '20px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '20px' }}>
          
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#10b981', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sliders size={16} /> 2. AI Recognition & Quality Thresholds
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              
              <div className="form-group">
                <label className="form-label">
                  Cosine Similarity Threshold: <b style={{ color: '#38bdf8' }}>{similarityThreshold}</b>
                </label>
                <input 
                  type="range" 
                  min="0.40" 
                  max="0.85" 
                  step="0.01" 
                  className="form-range" 
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(e.target.value)}
                  style={{ width: '100%' }}
                />
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
                  Recommended: <b>0.60</b>. Higher = stricter match, Lower = lenient.
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Min Face Sharpness Score: <b style={{ color: '#10b981' }}>{minQuality}</b>
                </label>
                <input 
                  type="range" 
                  min="10" 
                  max="60" 
                  step="1" 
                  className="form-range" 
                  value={minQuality}
                  onChange={(e) => setMinQuality(e.target.value)}
                  style={{ width: '100%' }}
                />
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
                  Ignores blurry faces. Recommended: <b>25.0 - 30.0</b>.
                </div>
              </div>

            </div>
          </div>

          {/* Section 3: Shift & Debounce Configuration */}
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '20px' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f59e0b', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Shield size={16} /> 3. Attendance Policy & Cooldown Windows
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              
              <div className="form-group">
                <label className="form-label">Attendance Debounce Window (Minutes)</label>
                <input 
                  type="number" 
                  min="1" 
                  max="120" 
                  className="form-input" 
                  value={cooldownMinutes}
                  onChange={(e) => setCooldownMinutes(e.target.value)}
                />
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
                  Prevents duplicate records if a person stands in front of the gate.
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Late Arrival Cutoff Time (24h format)</label>
                <input 
                  type="time" 
                  className="form-input" 
                  value={lateTime}
                  onChange={(e) => setLateTime(e.target.value)}
                />
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
                  Entries after this time are marked as <b>Late</b>.
                </div>
              </div>

            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }} disabled={loading}>
            <Save size={16} />
            <span>{loading ? "Applying Settings..." : "Save Configuration & Reload System"}</span>
          </button>

        </form>
      </div>

    </div>
  );
}
