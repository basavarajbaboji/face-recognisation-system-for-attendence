import React, { useState, useEffect, useRef } from 'react';
import { 
  Users, 
  CheckCircle2, 
  XCircle, 
  UserX, 
  Activity, 
  Clock, 
  Sparkles,
  Maximize2,
  UserPlus,
  Grid,
  Square,
  Plus,
  Camera,
  Video,
  X,
  Check,
  Upload,
  RefreshCw,
  AlertCircle,
  MapPin,
  Footprints,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export default function GateMonitor({ voiceEnabled }) {
  const [summary, setSummary] = useState({
    total_enrolled: 0,
    present_count: 0,
    absent_count: 0,
    late_count: 0,
    unknown_count: 0
  });

  const [telemetry, setTelemetry] = useState({
    crowd_headcount: 0,
    confirmed_count: 0,
    candidate_count: 0,
    unknown_count: 0,
    cameras: [],
    tracks: [],
    recent_events: []
  });

  // Multi-Camera Management State
  const [cameraList, setCameraList] = useState([
    { id: 'cam_1', name: 'Main Campus Gate - Entry A', source: '0', fps: 30, headcount: 0 }
  ]);
  const [selectedCamId, setSelectedCamId] = useState('cam_1');
  const [viewMode, setViewMode] = useState('single'); // 'single' or 'grid'
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());
  const [spokenEvents, setSpokenEvents] = useState(new Set());
  const [expandedTrails, setExpandedTrails] = useState(new Set());

  const toggleTrail = (id) => {
    setExpandedTrails(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Modals State
  const [showEnrollModal, setShowEnrollModal] = useState(false);
  const [showAddCamModal, setShowAddCamModal] = useState(false);

  // Quick Enrollment Form State
  const [enrollName, setEnrollName] = useState('');
  const [enrollRoll, setEnrollRoll] = useState('');
  const [enrollDept, setEnrollDept] = useState('Computer Science');
  const [enrollRole, setEnrollRole] = useState('student');
  const [enrollPhotoFile, setEnrollPhotoFile] = useState(null);
  const [enrollPhotoPreview, setEnrollPhotoPreview] = useState(null);
  const [enrollLoading, setEnrollLoading] = useState(false);
  const [enrollStatus, setEnrollStatus] = useState(null);

  // Add Camera Form State
  const [newCamName, setNewCamName] = useState('');
  const [newCamSource, setNewCamSource] = useState('0');
  const [addCamLoading, setAddCamLoading] = useState(false);
  const [detectedHardware, setDetectedHardware] = useState([]);
  const [scanningHardware, setScanningHardware] = useState(false);

  const canvasRef = useRef(null);
  const videoImgRef = useRef(null);
  const latestTelemetryRef = useRef(telemetry);
  const lastStateUpdateRef = useRef(0);

  const departments = ['Computer Science', 'Mechanical', 'Electrical', 'Civil', 'Electronics', 'Information Tech', 'Management / MBA'];

  // Fetch High-Level Summary Stats
  const fetchSummary = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/attendance/summary');
      if (res.ok) {
        setSummary(await res.json());
      }
    } catch (e) {
      console.warn("Could not fetch summary:", e);
    }
  };

  // Fetch Cameras List
  const fetchCameras = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/camera/list');
      if (res.ok) {
        const data = await res.json();
        if (data && data.length > 0) {
          setCameraList(data);
          // If selected cam deleted, default to first
          if (!data.some(c => c.id === selectedCamId)) {
            setSelectedCamId(data[0].id);
          }
        }
      }
    } catch (e) {
      console.warn("Could not fetch cameras:", e);
    }
  };

  // Real Hardware Scanner
  const fetchHardware = async () => {
    setScanningHardware(true);
    try {
      const res = await fetch('http://localhost:8000/api/camera/detect');
      if (res.ok) {
        setDetectedHardware(await res.json());
      }
    } catch (e) {
      console.warn("Could not detect cameras:", e);
    } finally {
      setScanningHardware(false);
    }
  };

  // Attach Camera to Process (Start AI Vision)
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
        await fetchHardware();
        setStreamKey(Date.now());
        setStreamError(false);
      }
    } catch (e) {
      alert("Error attaching camera: " + e.message);
    }
  };

  // Detach Camera from Process (Release Hardware Handle, 0% CPU)
  const handleDetachCamera = async (camId) => {
    try {
      const res = await fetch('http://localhost:8000/api/camera/detach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: camId })
      });
      if (res.ok) {
        await fetchCameras();
        await fetchHardware();
        setStreamKey(Date.now());
      }
    } catch (e) {
      alert("Error detaching camera: " + e.message);
    }
  };

  useEffect(() => {
    fetchSummary();
    fetchCameras();
    const interval = setInterval(() => {
      fetchSummary();
      fetchCameras();
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // High-performance canvas bounding box HUD renderer
  const drawHUD = (data) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!data.tracks || data.tracks.length === 0) return;

    const fw = data.frame_width || 1280;
    const fh = data.frame_height || 720;
    const scaleX = canvas.width / fw;
    const scaleY = canvas.height / fh;

    // Filter tracks for active camera if in single mode
    const tracksToDraw = viewMode === 'single' && selectedCamId
      ? data.tracks.filter(t => !t.cam_id || t.cam_id === selectedCamId)
      : data.tracks;

    tracksToDraw.forEach((track) => {
      const rawX = track.bbox[0];
      const rawY = track.bbox[1];
      const rawW = track.bbox[2];
      const rawH = track.bbox[3];

      const x = rawX * scaleX;
      const y = rawY * scaleY;
      const w = rawW * scaleX;
      const h = rawH * scaleY;

      const state = track.state;
      const label = track.label;
      const conf = track.confidence;
      
      let strokeColor = '#f97316'; // Orange for Unknown
      let fillColor = 'rgba(249, 115, 22, 0.12)';
      let badgeColor = '#f97316';

      if (state === 'CONFIRMED') {
        strokeColor = '#10b981'; // Green
        fillColor = 'rgba(16, 185, 129, 0.15)';
        badgeColor = '#10b981';
      } else if (state === 'CANDIDATE') {
        strokeColor = '#f59e0b'; // Yellow
        fillColor = 'rgba(245, 158, 11, 0.15)';
        badgeColor = '#f59e0b';
      }

      // Draw Glowing Bounding Box
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2.5;
      ctx.fillStyle = fillColor;
      ctx.strokeRect(x, y, w, h);
      ctx.fillRect(x, y, w, h);

      // Corner Accents
      const len = Math.min(w, h) * 0.22;
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 3;
      
      ctx.beginPath();
      ctx.moveTo(x, y + len); ctx.lineTo(x, y); ctx.lineTo(x + len, y);
      ctx.stroke();
      
      ctx.beginPath();
      ctx.moveTo(x + w - len, y + h); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w, y + h - len);
      ctx.stroke();

      // Label Badge
      const text = state === 'CONFIRMED' ? `${label} • ${Math.round(conf * 100)}%` : label;
      ctx.font = '600 13px Inter, sans-serif';
      const textMetrics = ctx.measureText(text);
      const bgWidth = textMetrics.width + 16;
      const bgHeight = 22;

      ctx.fillStyle = badgeColor;
      ctx.fillRect(x, Math.max(0, y - bgHeight - 4), bgWidth, bgHeight);

      ctx.fillStyle = '#041322';
      ctx.fillText(text, x + 8, Math.max(16, y - 8));
    });
  };

  // WebSocket Live Telemetry Stream
  useEffect(() => {
    let ws = null;
    let isMounted = true;

    const connectWs = () => {
      ws = new WebSocket('ws://localhost:8000/api/camera/ws');
      
      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data);
          latestTelemetryRef.current = data;
          setStreamError(false);

          drawHUD(data);

          const now = Date.now();
          const prevEventsCount = latestTelemetryRef.current.recent_events ? latestTelemetryRef.current.recent_events.length : 0;
          const currEventsCount = data.recent_events ? data.recent_events.length : 0;
          const hasNewEvent = currEventsCount !== prevEventsCount;

          if (hasNewEvent || (now - lastStateUpdateRef.current > 250)) {
            lastStateUpdateRef.current = now;
            setTelemetry(data);
          }
          
          // Handle Voice Greetings for new attendance events
          if (voiceEnabled && data.recent_events && data.recent_events.length > 0) {
            const latest = data.recent_events[data.recent_events.length - 1];
            if (latest && !spokenEvents.has(latest.id)) {
              spokenEvents.add(latest.id);
              const cleanName = latest.label.split('(')[0].trim();
              const utterance = new SpeechSynthesisUtterance(`Welcome ${cleanName}`);
              utterance.rate = 1.0;
              window.speechSynthesis.speak(utterance);
            }
          }
        } catch (e) {
          console.error("WS Parse error:", e);
        }
      };

      ws.onerror = () => {
        if (isMounted) setStreamError(true);
      };

      ws.onclose = () => {
        if (isMounted) {
          setTimeout(connectWs, 2500);
        }
      };
    };

    connectWs();
    return () => {
      isMounted = false;
      if (ws) ws.close();
    };
  }, [voiceEnabled, spokenEvents, viewMode, selectedCamId]);

  const reloadStream = () => {
    setStreamError(false);
    setStreamKey(Date.now());
  };

  // Handle Snapshot Capture from Live Stream for Quick Enrollment
  const captureSnapshotFromStream = () => {
    const videoImg = videoImgRef.current;
    if (!videoImg) return;

    try {
      const canvas = document.createElement('canvas');
      canvas.width = videoImg.naturalWidth || 640;
      canvas.height = videoImg.naturalHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoImg, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
      setEnrollPhotoPreview(dataUrl);
      setEnrollPhotoFile(null); // Indicates using base64 snapshot
    } catch (e) {
      alert("Snapshot capture requires image loaded: " + e.message);
    }
  };

  // Handle Photo File Upload
  const handlePhotoFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setEnrollPhotoFile(file);
      setEnrollPhotoPreview(URL.createObjectURL(file));
    }
  };

  // Submit Quick Enrollment
  const handleQuickEnrollSubmit = async (e) => {
    e.preventDefault();
    if (!enrollPhotoFile && !enrollPhotoPreview) {
      alert("Please upload a photo or capture a camera snapshot first.");
      return;
    }

    setEnrollLoading(true);
    setEnrollStatus(null);

    try {
      const formData = new FormData();
      formData.append('name', enrollName.trim());
      formData.append('roll_number', enrollRoll.trim());
      formData.append('department', enrollDept);
      formData.append('role', enrollRole);

      if (enrollPhotoFile) {
        formData.append('photo_file', enrollPhotoFile);
      } else if (enrollPhotoPreview) {
        formData.append('photo_base64', enrollPhotoPreview);
      }

      const res = await fetch('http://localhost:8000/api/users/quick-enroll', {
        method: 'POST',
        body: formData
      });

      const resData = await res.json();

      if (res.ok) {
        setEnrollStatus({ type: 'success', message: resData.message });
        fetchSummary();
        setTimeout(() => {
          setShowEnrollModal(false);
          setEnrollName('');
          setEnrollRoll('');
          setEnrollPhotoFile(null);
          setEnrollPhotoPreview(null);
          setEnrollStatus(null);
        }, 1800);
      } else {
        setEnrollStatus({ type: 'error', message: resData.detail || 'Enrollment failed.' });
      }
    } catch (err) {
      setEnrollStatus({ type: 'error', message: err.message });
    } finally {
      setEnrollLoading(false);
    }
  };

  // Submit Add New Camera
  const handleAddCameraSubmit = async (e) => {
    e.preventDefault();
    setAddCamLoading(true);
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
        setShowAddCamModal(false);
        setNewCamName('');
        setNewCamSource('0');
      } else {
        alert("Could not add camera.");
      }
    } catch (e) {
      alert("Error adding camera: " + e.message);
    } finally {
      setAddCamLoading(false);
    }
  };

  const activeCam = cameraList.find(c => c.id === selectedCamId) || cameraList[0] || { name: 'Main Camera', fps: 30 };

  return (
    <div>
      {/* Top Stat Counters */}
      <div className="stat-grid">
        <div className="stat-card glass-panel enrolled">
          <div className="stat-info">
            <div className="stat-label">Enrolled Total</div>
            <div className="stat-value">{summary.total_enrolled}</div>
          </div>
          <div className="stat-icon" style={{ background: 'rgba(56, 189, 248, 0.1)' }}>
            <Users size={22} color="#38bdf8" />
          </div>
        </div>

        <div className="stat-card glass-panel present">
          <div className="stat-info">
            <div className="stat-label">Present Today</div>
            <div className="stat-value" style={{ color: '#10b981' }}>{summary.present_count}</div>
          </div>
          <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
            <CheckCircle2 size={22} color="#10b981" />
          </div>
        </div>

        <div className="stat-card glass-panel absent">
          <div className="stat-info">
            <div className="stat-label">Absent Today</div>
            <div className="stat-value" style={{ color: '#f43f5e' }}>{summary.absent_count}</div>
          </div>
          <div className="stat-icon" style={{ background: 'rgba(244, 63, 94, 0.1)' }}>
            <XCircle size={22} color="#f43f5e" />
          </div>
        </div>

        <div className="stat-card glass-panel unknown">
          <div className="stat-info">
            <div className="stat-label">Unknown Visitors</div>
            <div className="stat-value" style={{ color: '#f97316' }}>{summary.unknown_count}</div>
          </div>
          <div className="stat-icon" style={{ background: 'rgba(249, 115, 22, 0.1)' }}>
            <UserX size={22} color="#f97316" />
          </div>
        </div>
      </div>

      {/* Surveillance Command Toolbar */}
      <div className="glass-panel" style={{ padding: '12px 18px', marginBottom: '18px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
        
        {/* Left: Camera Selector Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginRight: '4px' }}>CCTV Feeds:</span>
          {cameraList.map((cam) => {
            const isAtt = cam.is_attached !== false;
            return (
              <button
                key={cam.id}
                className={`btn ${selectedCamId === cam.id && viewMode === 'single' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '5px 12px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                onClick={() => {
                  setSelectedCamId(cam.id);
                  setViewMode('single');
                  setStreamError(false);
                  setStreamKey(Date.now());
                }}
              >
                <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: isAtt ? '#10b981' : '#64748b' }}></div>
                <Video size={14} />
                <span>{cam.name}</span>
                <span style={{ fontSize: '0.7rem', opacity: 0.8 }} className="font-mono">
                  ({isAtt ? `${cam.fps || 30} FPS` : 'Detached'})
                </span>
              </button>
            );
          })}

          <button 
            className="btn btn-secondary" 
            style={{ padding: '5px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px', borderStyle: 'dashed' }}
            onClick={() => {
              fetchHardware();
              setShowAddCamModal(true);
            }}
            title="Attach a new CCTV camera or RTSP stream"
          >
            <Plus size={14} />
            <span>Add / Scan Camera</span>
          </button>
        </div>

        {/* Right: Grid Toggle & Quick Enroll Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          
          {/* View Mode Toggle: Single vs Multi-Cam Grid */}
          <div className="nav-links" style={{ padding: '2px' }}>
            <button 
              className={`nav-item ${viewMode === 'single' ? 'active' : ''}`}
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
              onClick={() => setViewMode('single')}
              title="Focus on single camera feed"
            >
              <Square size={14} />
              <span>Single</span>
            </button>

            <button 
              className={`nav-item ${viewMode === 'grid' ? 'active' : ''}`}
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
              onClick={() => setViewMode('grid')}
              title="View all cameras simultaneously in grid"
            >
              <Grid size={14} />
              <span>Grid ({cameraList.length})</span>
            </button>
          </div>

          {/* Quick Enroll Person (Highlighted Action) */}
          <button 
            className="btn btn-primary"
            style={{ 
              padding: '6px 14px', 
              fontSize: '0.82rem', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px',
              boxShadow: '0 0 15px -3px var(--primary-glow)'
            }}
            onClick={() => setShowEnrollModal(true)}
          >
            <UserPlus size={16} />
            <span>➕ Quick Enroll Person</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Video Stream (65%) + Activity Feed (35%) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(320px, 1fr)', gap: '20px' }}>
        
        {/* Left: Video Feed with Canvas HUD */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="pulse-dot" style={{ background: activeCam.is_attached !== false ? '#10b981' : '#64748b' }}></span>
              <h2 className="font-heading" style={{ fontSize: '1.05rem', fontWeight: 600 }}>
                {viewMode === 'single' ? activeCam.name : `CCTV Multi-Camera Matrix (${cameraList.length} Feeds)`}
              </h2>
              {viewMode === 'single' && (
                <span className={`badge ${activeCam.is_attached !== false ? 'badge-confirmed' : 'badge-candidate'}`} style={{ fontSize: '0.68rem' }}>
                  {activeCam.is_attached !== false ? 'Active Process' : 'Detached (0% CPU)'}
                </span>
              )}
            </div>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {viewMode === 'single' && (
                activeCam.is_attached !== false ? (
                  <button 
                    className="btn btn-secondary" 
                    style={{ padding: '3px 8px', fontSize: '0.72rem', color: '#f43f5e', borderColor: 'rgba(244, 63, 94, 0.35)' }}
                    onClick={() => handleDetachCamera(activeCam.id)}
                    title="Detach camera to stop AI process and release physical hardware handle"
                  >
                    ⏹ Detach from Process
                  </button>
                ) : (
                  <button 
                    className="btn btn-primary" 
                    style={{ padding: '3px 10px', fontSize: '0.72rem' }}
                    onClick={() => handleAttachCamera(activeCam)}
                    title="Attach camera to start AI face recognition"
                  >
                    ▶ Attach to Process
                  </button>
                )
              )}

              <button 
                className="btn btn-secondary" 
                style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                onClick={reloadStream}
                title="Refresh video stream"
              >
                <RefreshCw size={12} />
              </button>

              <span className="font-mono" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                FPS: {activeCam.is_attached !== false ? (activeCam.fps || 30) : 0} • Headcount: <b style={{ color: '#38bdf8' }}>{telemetry.crowd_headcount || 0}</b>
              </span>
            </div>
          </div>

          {/* Single Camera View */}
          {viewMode === 'single' && (
            <div style={{ position: 'relative', width: '100%', borderRadius: '12px', overflow: 'hidden', background: '#020617', aspectRatio: '16/9', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {activeCam.is_attached !== false ? (
                <>
                  <img 
                    key={`${selectedCamId}-${streamKey}`}
                    ref={videoImgRef}
                    src={`http://localhost:8000/api/camera/${selectedCamId}/stream?t=${streamKey}`} 
                    alt="Live Gate Stream" 
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: streamError ? 'none' : 'block' }}
                    onError={() => setStreamError(true)}
                  />

                  {streamError && (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>
                      <p style={{ color: '#f43f5e', fontWeight: 600, marginBottom: '8px' }}>Camera Stream Connecting...</p>
                      <button className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '0.8rem' }} onClick={reloadStream}>
                        Retry Stream Connection
                      </button>
                    </div>
                  )}

                  {/* Canvas HUD Overlay */}
                  <canvas 
                    ref={canvasRef}
                    width={1280}
                    height={720}
                    style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
                  />
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: '#94a3b8' }}>
                  <Video size={48} color="#64748b" style={{ margin: '0 auto 12px' }} />
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
                    {activeCam.name} is Detached
                  </h3>
                  <p style={{ fontSize: '0.82rem', color: '#94a3b8', maxWidth: '420px', margin: '0 auto 18px', lineHeight: 1.5 }}>
                    The camera hardware handle is released. Background AI vision and face recognition workers are stopped, consuming 0% CPU.
                  </p>
                  <button 
                    className="btn btn-primary" 
                    style={{ padding: '8px 22px', fontSize: '0.86rem', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                    onClick={() => handleAttachCamera(activeCam)}
                  >
                    ▶ Click to Use (Attach to Process)
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Multi-Camera Grid View */}
          {viewMode === 'grid' && (
            <div className="cctv-grid">
              {cameraList.map((cam) => {
                const isAtt = cam.is_attached !== false;
                return (
                  <div key={cam.id} className="cctv-card" style={{ position: 'relative' }}>
                    {isAtt ? (
                      <>
                        <img 
                          src={`http://localhost:8000/api/camera/${cam.id}/stream?t=${streamKey}`} 
                          alt={cam.name}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                        <div style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(2, 6, 23, 0.75)', padding: '3px 8px', borderRadius: '4px', fontSize: '0.72rem', color: '#f8fafc', fontWeight: 600 }}>
                          {cam.name}
                        </div>
                        <div style={{ position: 'absolute', bottom: 8, right: 8, background: 'rgba(2, 6, 23, 0.75)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.68rem', color: '#38bdf8' }} className="font-mono">
                          {cam.fps || 30} FPS
                        </div>
                      </>
                    ) : (
                      <div style={{ height: '100%', minHeight: '160px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(2, 6, 23, 0.95)', padding: '16px', textAlign: 'center' }}>
                        <Video size={28} color="#64748b" style={{ marginBottom: '6px' }} />
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc', marginBottom: '2px' }}>{cam.name}</div>
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginBottom: '10px' }}>Detached (0% CPU)</div>
                        <button className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '0.74rem' }} onClick={() => handleAttachCamera(cam)}>
                          ▶ Use Camera
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Quick HUD Legend */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', marginTop: '14px', fontSize: '0.78rem', color: '#94a3b8' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', background: '#10b981', borderRadius: '2px' }}></span>
              Confirmed Enrolled (Green)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', background: '#f59e0b', borderRadius: '2px' }}></span>
              Verifying Candidate (Yellow)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', background: '#f97316', borderRadius: '2px' }}></span>
              Unknown Visitor (Orange)
            </span>
          </div>
        </div>

        {/* Right: Live Gate Activity Feed & Unknown Visitor Tray */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          
          {/* Unknown Visitor Quick Action Tray */}
          {summary.unknown_count > 0 && (
            <div className="glass-panel" style={{ padding: '14px', background: 'rgba(249, 115, 22, 0.08)', border: '1px solid rgba(249, 115, 22, 0.3)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f97316', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <UserX size={16} /> Unknown Visitors Detected ({summary.unknown_count})
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '10px' }}>
                Unrecognized faces are tracked at the gate. Click below to enroll yourself or any visitor instantly.
              </p>
              <button 
                className="btn btn-secondary" 
                style={{ width: '100%', padding: '6px', fontSize: '0.78rem', color: '#f97316', borderColor: 'rgba(249, 115, 22, 0.4)' }}
                onClick={() => {
                  captureSnapshotFromStream();
                  setShowEnrollModal(true);
                }}
              >
                Enroll Current Face Snapshot
              </button>
            </div>
          )}

          {/* Activity Feed */}
          <div className="glass-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={18} color="#38bdf8" />
                <h3 className="font-heading" style={{ fontSize: '1.05rem', fontWeight: 600 }}>Live Gate Activity Feed</h3>
              </div>
              <span className="badge badge-confirmed" style={{ fontSize: '0.72rem' }}>Real-time</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: '480px', paddingRight: '4px' }}>
              {telemetry.recent_events && telemetry.recent_events.length > 0 ? (
                telemetry.recent_events.map((ev) => {
                  const isExpanded = expandedTrails.has(ev.id);
                  return (
                    <div 
                      key={ev.id} 
                      className="glass-panel" 
                      style={{ 
                        padding: '12px 14px', 
                        background: 'rgba(255, 255, 255, 0.03)',
                        borderLeft: `4px solid ${ev.status === 'Late' ? '#f59e0b' : '#10b981'}`,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.92rem', color: '#f8fafc', marginBottom: '3px' }}>
                            {ev.label}
                          </div>
                          {/* Footprint Highlights: When Entered, Where, Sightings */}
                          <div style={{ fontSize: '0.74rem', color: '#94a3b8', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#10b981' }}>
                              <Clock size={12} />
                              <span>Entered: <strong className="font-mono">{ev.first_seen || ev.time}</strong></span>
                            </span>
                            <span>•</span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#38bdf8' }}>
                              <MapPin size={12} />
                              <span>{ev.current_gate || ev.entry_gate || 'Main Gate'}</span>
                            </span>
                            <span>•</span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#e2e8f0' }}>
                              <Footprints size={12} color="#a855f7" />
                              <span><strong className="font-mono">{ev.seen_count || 1}</strong> {ev.seen_count === 1 ? 'sighting' : 'sightings'}</span>
                            </span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                          <span className={`badge ${ev.status === 'Late' ? 'badge-late' : 'badge-present'}`}>
                            {ev.status}
                          </span>
                          <span style={{ fontSize: '0.68rem', color: '#64748b' }}>
                            Last: <span className="font-mono">{ev.time}</span>
                          </span>
                        </div>
                      </div>

                      {/* Footprint Audit Trail Toggle */}
                      {ev.trail && ev.trail.length > 0 && (
                        <div>
                          <button
                            type="button"
                            onClick={() => toggleTrail(ev.id)}
                            style={{
                              background: 'rgba(255, 255, 255, 0.04)',
                              border: '1px solid rgba(255, 255, 255, 0.08)',
                              borderRadius: '4px',
                              padding: '3px 8px',
                              fontSize: '0.7rem',
                              color: '#94a3b8',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '5px'
                            }}
                          >
                            <Footprints size={11} color="#a855f7" />
                            <span>Footprint Trail ({ev.trail.length} checkpoints)</span>
                            {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          </button>

                          {isExpanded && (
                            <div style={{ 
                              marginTop: '8px', 
                              padding: '8px 10px', 
                              background: 'rgba(0, 0, 0, 0.35)', 
                              borderRadius: '6px',
                              border: '1px solid rgba(255, 255, 255, 0.06)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px'
                            }}>
                              <div style={{ fontSize: '0.66rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
                                Campus Movement Audit Trail
                              </div>
                              {ev.trail.map((pt, pIdx) => (
                                <div key={pIdx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.72rem' }}>
                                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: pIdx === 0 ? '#10b981' : (pIdx === ev.trail.length - 1 ? '#38bdf8' : '#a855f7') }}></span>
                                  <span className="font-mono" style={{ color: '#cbd5e1' }}>{pt.time}</span>
                                  <span style={{ color: '#94a3b8' }}>@</span>
                                  <span style={{ color: '#f1f5f9', fontWeight: 500 }}>{pt.gate}</span>
                                  <span className="badge" style={{ fontSize: '0.6rem', padding: '1px 5px', background: 'rgba(255, 255, 255, 0.06)' }}>
                                    {pt.type || 'Detection'}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 10px', color: '#64748b', fontSize: '0.85rem' }}>
                  <Clock size={32} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
                  <div>Awaiting gate recognition events...</div>
                  <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>Identified students and faculty will appear here instantly.</div>
                </div>
              )}
            </div>
          </div>

        </div>

      </div>

      {/* ========================================================================= */}
      {/* QUICK ENROLL PERSON MODAL */}
      {/* ========================================================================= */}
      {showEnrollModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <UserPlus size={20} color="#38bdf8" />
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Quick Person Enrollment</h3>
                  <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Upload a photo or capture from live webcam to make them detectable instantly.</p>
                </div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 8px' }}
                onClick={() => setShowEnrollModal(false)}
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleQuickEnrollSubmit} style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Feedback Alert */}
              {enrollStatus && (
                <div 
                  className="glass-panel" 
                  style={{ 
                    padding: '12px 16px', 
                    background: enrollStatus.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                    borderLeft: `4px solid ${enrollStatus.type === 'success' ? '#10b981' : '#f43f5e'}`,
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '10px' 
                  }}
                >
                  {enrollStatus.type === 'success' ? <CheckCircle2 size={18} color="#10b981" /> : <AlertCircle size={18} color="#f43f5e" />}
                  <span style={{ fontSize: '0.85rem', color: enrollStatus.type === 'success' ? '#10b981' : '#f43f5e', fontWeight: 500 }}>
                    {enrollStatus.message}
                  </span>
                </div>
              )}

              {/* Photo Input Area */}
              <div>
                <label className="form-label" style={{ marginBottom: '8px', display: 'block' }}>Face Photo (Upload or Live Snapshot)</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  
                  {/* File Upload Button */}
                  <label 
                    className="btn btn-secondary" 
                    style={{ 
                      padding: '16px', 
                      display: 'flex', 
                      flexDirection: 'column', 
                      alignItems: 'center', 
                      gap: '8px', 
                      cursor: 'pointer',
                      border: '1px dashed rgba(255, 255, 255, 0.2)'
                    }}
                  >
                    <Upload size={20} color="#38bdf8" />
                    <span style={{ fontSize: '0.78rem' }}>Upload Photo File</span>
                    <input 
                      type="file" 
                      accept="image/*" 
                      style={{ display: 'none' }} 
                      onChange={handlePhotoFileChange}
                    />
                  </label>

                  {/* Camera Snapshot Button */}
                  <button 
                    type="button"
                    className="btn btn-secondary" 
                    style={{ 
                      padding: '16px', 
                      display: 'flex', 
                      flexDirection: 'column', 
                      alignItems: 'center', 
                      gap: '8px', 
                      border: '1px dashed rgba(56, 189, 248, 0.3)'
                    }}
                    onClick={captureSnapshotFromStream}
                  >
                    <Camera size={20} color="#10b981" />
                    <span style={{ fontSize: '0.78rem' }}>Snap from Live Camera</span>
                  </button>
                </div>

                {/* Photo Preview */}
                {enrollPhotoPreview && (
                  <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '12px', padding: '10px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
                    <img 
                      src={enrollPhotoPreview} 
                      alt="Preview" 
                      style={{ width: '64px', height: '64px', borderRadius: '8px', objectFit: 'cover', border: '2px solid #38bdf8' }} 
                    />
                    <div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Check size={14} /> Photo Loaded Ready for Enrollment
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                        ArcFace AI will automatically align face and extract 512-d feature vector.
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Attributes Form Fields */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Full Name *</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="e.g. John Doe"
                    value={enrollName}
                    onChange={(e) => setEnrollName(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Roll Number / ID *</label>
                  <input 
                    type="text" 
                    className="form-input font-mono" 
                    placeholder="e.g. CS2026-042"
                    value={enrollRoll}
                    onChange={(e) => setEnrollRoll(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Department</label>
                  <select 
                    className="form-select"
                    value={enrollDept}
                    onChange={(e) => setEnrollDept(e.target.value)}
                  >
                    {departments.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Role</label>
                  <select 
                    className="form-select"
                    value={enrollRole}
                    onChange={(e) => setEnrollRole(e.target.value)}
                  >
                    <option value="student">Student</option>
                    <option value="faculty">Faculty</option>
                    <option value="staff">Staff</option>
                    <option value="visitor">Registered Visitor</option>
                  </select>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setShowEnrollModal(false)}
                >
                  Cancel
                </button>

                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={enrollLoading}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 18px' }}
                >
                  {enrollLoading ? <RefreshCw size={16} className="animate-spin" /> : <Sparkles size={16} />}
                  <span>{enrollLoading ? "Enrolling Face..." : "Enroll & Make Detectable"}</span>
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* ADD CCTV CAMERA MODAL */}
      {/* ========================================================================= */}
      {showAddCamModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog" style={{ maxWidth: '520px' }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Video size={20} color="#38bdf8" />
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Attach CCTV / Webcam</h3>
                  <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Real hardware auto-detection or RTSP network IP camera feeds.</p>
                </div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 8px' }}
                onClick={() => setShowAddCamModal(false)}
              >
                <X size={16} />
              </button>
            </div>

            <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Hardware Detected Webcams */}
              <div style={{ background: 'rgba(56, 189, 248, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(56, 189, 248, 0.15)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#38bdf8' }}>Detected USB / Internal Webcams:</span>
                  <button 
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: '2px 8px', fontSize: '0.7rem' }}
                    onClick={fetchHardware}
                    disabled={scanningHardware}
                  >
                    <RefreshCw size={11} className={scanningHardware ? "animate-spin" : ""} />
                    <span>{scanningHardware ? "Scanning..." : "Rescan"}</span>
                  </button>
                </div>

                {detectedHardware.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {detectedHardware.map((hw) => (
                      <div key={hw.source} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(2, 6, 23, 0.6)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                        <div>
                          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f8fafc' }}>{hw.name}</div>
                          <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Device Index {hw.source} • {hw.resolution}</div>
                        </div>

                        {hw.is_attached ? (
                          <span className="badge badge-confirmed" style={{ fontSize: '0.68rem' }}>Active in Process</span>
                        ) : (
                          <button 
                            type="button"
                            className="btn btn-primary"
                            style={{ padding: '4px 10px', fontSize: '0.74rem' }}
                            onClick={async () => {
                              await handleAttachCamera({
                                id: `cam_${hw.source}`,
                                name: `Webcam (Device ${hw.source})`,
                                source: hw.source
                              });
                              setShowAddCamModal(false);
                            }}
                          >
                            ▶ Click to Use
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.78rem', color: '#64748b', textAlign: 'center', padding: '8px' }}>
                    {scanningHardware ? "Detecting physical camera hardware..." : "Click Rescan to detect USB webcams."}
                  </div>
                )}
              </div>

              {/* Custom RTSP / Network / Index Form */}
              <form onSubmit={handleAddCameraSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#e2e8f0', marginTop: '4px' }}>
                  Or Add Custom RTSP / Network Stream:
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Camera / Gate Name *</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="e.g. South Gate - Exit B or Library Corridor"
                    value={newCamName}
                    onChange={(e) => setNewCamName(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Video Source (Index or RTSP URL) *</label>
                  <input 
                    type="text" 
                    className="form-input font-mono" 
                    placeholder="e.g. 1 or rtsp://admin:12345@192.168.1.50:554/stream"
                    value={newCamSource}
                    onChange={(e) => setNewCamSource(e.target.value)}
                    required
                  />
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
                    Use <code>0</code> for primary webcam, <code>1</code> for secondary USB camera, or an <code>rtsp://...</code> network URL.
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
                  <button 
                    type="button" 
                    className="btn btn-secondary" 
                    onClick={() => setShowAddCamModal(false)}
                  >
                    Cancel
                  </button>

                  <button 
                    type="submit" 
                    className="btn btn-primary"
                    disabled={addCamLoading}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    {addCamLoading ? <RefreshCw size={16} className="animate-spin" /> : <Plus size={16} />}
                    <span>{addCamLoading ? "Connecting..." : "Connect Camera"}</span>
                  </button>
                </div>
              </form>

            </div>
          </div>
        </div>
      )}

    </div>
  );
}
