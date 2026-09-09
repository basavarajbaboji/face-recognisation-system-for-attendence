import React, { useState, useEffect, useRef } from 'react';
import { 
  UserPlus, 
  Upload, 
  Camera, 
  Trash2, 
  CheckCircle, 
  AlertCircle, 
  Search, 
  FileArchive,
  Layers,
  Sparkles,
  RefreshCw,
  X
} from 'lucide-react';
import { API_BASE } from '../config';

export default function Enrollment() {
  const [enrollMode, setEnrollMode] = useState('single'); // 'single' or 'bulk'
  const [usersList, setUsersList] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Single Enrollment Form State
  const [rollNumber, setRollNumber] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('student');
  const [department, setDepartment] = useState('Computer Science');
  const [year, setYear] = useState('1st Year');
  const [email, setEmail] = useState('');

  // 3-Angle Photos State (Files or Blob URLs)
  const [frontPhoto, setFrontPhoto] = useState(null);
  const [leftPhoto, setLeftPhoto] = useState(null);
  const [rightPhoto, setRightPhoto] = useState(null);

  // Webcam Capture Modal / Stream
  const [isCapturing, setIsCapturing] = useState(false);
  const [activeAngleTarget, setActiveAngleTarget] = useState('front'); // 'front', 'left', 'right'
  const videoRef = useRef(null);

  // Bulk ZIP State
  const [bulkZipFile, setBulkZipFile] = useState(null);
  const [bulkProgress, setBulkProgress] = useState(null);

  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);
  const [deleteConfirmUser, setDeleteConfirmUser] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const departments = ['Computer Science', 'Mechanical', 'Electrical', 'Civil', 'Electronics', 'Information Tech', 'Management / MBA'];

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/users/`);
      if (res.ok) {
        setUsersList(await res.json());
      }
    } catch (e) {
      console.error("Error fetching enrolled users:", e);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // Start Webcam Stream for 3-Angle Capture
  const startCamera = async (targetAngle) => {
    setActiveAngleTarget(targetAngle);
    setIsCapturing(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (e) {
      alert("Could not access local webcam for photo capture: " + e.message);
      setIsCapturing(false);
    }
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      const file = new File([blob], `${rollNumber || 'user'}_${activeAngleTarget}.jpg`, { type: 'image/jpeg' });
      if (activeAngleTarget === 'front') setFrontPhoto(file);
      else if (activeAngleTarget === 'left') setLeftPhoto(file);
      else if (activeAngleTarget === 'right') setRightPhoto(file);
      
      // Stop Camera
      if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
      }
      setIsCapturing(false);
    }, 'image/jpeg', 0.95);
  };

  const handleSingleSubmit = async (e) => {
    e.preventDefault();
    if (!frontPhoto) {
      alert("Please capture or upload at least the Frontal Face Photo.");
      return;
    }
    setLoading(true);
    setMsg(null);

    const formData = new FormData();
    formData.append('roll_number', rollNumber);
    formData.append('name', name);
    formData.append('role', role);
    formData.append('department', department);
    formData.append('year', year);
    if (email) formData.append('email', email);
    formData.append('front_photo', frontPhoto);
    if (leftPhoto) formData.append('left_photo', leftPhoto);
    if (rightPhoto) formData.append('right_photo', rightPhoto);

    try {
      const res = await fetch(`${API_BASE}/api/users/enroll-single`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setMsg({ type: 'success', text: `Successfully enrolled ${name} with multi-angle templates!` });
        setRollNumber('');
        setName('');
        setEmail('');
        setFrontPhoto(null);
        setLeftPhoto(null);
        setRightPhoto(null);
        fetchUsers();
      } else {
        setMsg({ type: 'error', text: data.detail || 'Failed to enroll user.' });
      }
    } catch (err) {
      setMsg({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleBulkUpload = async (e) => {
    e.preventDefault();
    if (!bulkZipFile) {
      alert("Please select a ZIP file containing photos.");
      return;
    }
    setLoading(true);
    setBulkProgress(null);
    
    const formData = new FormData();
    formData.append('zip_file', bulkZipFile);
    formData.append('default_department', department);
    formData.append('default_role', role);

    try {
      const res = await fetch(`${API_BASE}/api/users/enroll-bulk-zip`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setBulkProgress(data);
        fetchUsers();
      } else {
        alert(data.detail || "Bulk import failed.");
      }
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const executeDeleteUser = async (userId, userName) => {
    setDeletingId(userId);
    try {
      const res = await fetch(`${API_BASE}/api/users/${userId}`, { method: 'DELETE' });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg({ type: 'success', text: `Successfully removed ${userName} and all associated templates.` });
        setDeleteConfirmUser(null);
        await fetchUsers();
      } else {
        setMsg({ type: 'error', text: `Failed to delete: ${data.detail || res.statusText}` });
      }
    } catch (e) {
      setMsg({ type: 'error', text: "Error deleting user: " + e.message });
    } finally {
      setDeletingId(null);
    }
  };

  const filteredUsers = usersList.filter(u => 
    u.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    u.roll_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.department.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Toggle: Guided Wizard vs Bulk ZIP */}
      <div className="glass-panel" style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="font-heading" style={{ fontSize: '1.2rem', fontWeight: 600 }}>Enrollment Command Wizard</h2>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Register students and faculty with multi-template face recognition.</p>
        </div>

        <div className="nav-links">
          <button 
            className={`nav-item ${enrollMode === 'single' ? 'active' : ''}`}
            onClick={() => setEnrollMode('single')}
          >
            <UserPlus size={16} />
            <span>Interactive 3-Angle Wizard</span>
          </button>

          <button 
            className={`nav-item ${enrollMode === 'bulk' ? 'active' : ''}`}
            onClick={() => setEnrollMode('bulk')}
          >
            <FileArchive size={16} />
            <span>Bulk ZIP Batch Importer</span>
          </button>
        </div>
      </div>

      {msg && (
        <div className="glass-panel" style={{ 
          padding: '12px 18px', 
          background: msg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
          borderLeft: `4px solid ${msg.type === 'success' ? '#10b981' : '#f43f5e'}`,
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          {msg.type === 'success' ? <CheckCircle size={18} color="#10b981" /> : <AlertCircle size={18} color="#f43f5e" />}
          <span style={{ fontSize: '0.88rem', fontWeight: 500 }}>{msg.text}</span>
        </div>
      )}

      {/* Mode 1: Interactive 3-Angle Wizard */}
      {enrollMode === 'single' && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <form onSubmit={handleSingleSubmit} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(320px, 1fr)', gap: '30px' }}>
            
            {/* Left Form Fields */}
            <div>
              <h3 className="font-heading" style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={18} color="#38bdf8" />
                Profile Information
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div className="form-group">
                  <label className="form-label">Roll / Faculty ID *</label>
                  <input 
                    type="text" 
                    className="form-input font-mono" 
                    placeholder="e.g. CS202401"
                    required
                    value={rollNumber}
                    onChange={(e) => setRollNumber(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Full Name *</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="e.g. Rahul Sharma"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
                <div className="form-group">
                  <label className="form-label">Role</label>
                  <select className="form-select" value={role} onChange={(e) => setRole(e.target.value)}>
                    <option value="student">Student</option>
                    <option value="faculty">Faculty</option>
                    <option value="staff">Staff</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Department</label>
                  <select className="form-select" value={department} onChange={(e) => setDepartment(e.target.value)}>
                    {departments.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Year / Semester</label>
                  <select className="form-select" value={year} onChange={(e) => setYear(e.target.value)}>
                    <option value="1st Year">1st Year</option>
                    <option value="2nd Year">2nd Year</option>
                    <option value="3rd Year">3rd Year</option>
                    <option value="4th Year">4th Year</option>
                    <option value="Faculty">Faculty (N/A)</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Email (Optional - for absent notices)</label>
                <input 
                  type="email" 
                  className="form-input" 
                  placeholder="student@college.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }} disabled={loading}>
                <UserPlus size={16} />
                <span>{loading ? "Extracting Embeddings & Enrolling..." : "Enroll Profile with 3-Angle Templates"}</span>
              </button>
            </div>

            {/* Right: 3-Angle Guided Capture Stations */}
            <div>
              <h3 className="font-heading" style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Camera size={18} color="#10b981" />
                Multi-Angle Face Capture
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
                
                {/* 1. Front Angle */}
                <div className="glass-panel" style={{ padding: '12px', textAlign: 'center', border: frontPhoto ? '2px solid #10b981' : '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '8px' }}>1. Front (0°) *</div>
                  <div style={{ width: '100%', height: '90px', background: '#020617', borderRadius: '8px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '8px' }}>
                    {frontPhoto ? (
                      <img src={URL.createObjectURL(frontPhoto)} alt="Front" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <Camera size={24} color="#64748b" />
                    )}
                  </div>
                  <button type="button" className="btn btn-secondary" style={{ width: '100%', padding: '6px', fontSize: '0.75rem' }} onClick={() => startCamera('front')}>
                    {frontPhoto ? "Re-Capture" : "Capture Front"}
                  </button>
                </div>

                {/* 2. Left Angle */}
                <div className="glass-panel" style={{ padding: '12px', textAlign: 'center', border: leftPhoto ? '2px solid #38bdf8' : '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '8px' }}>2. Left (20°)</div>
                  <div style={{ width: '100%', height: '90px', background: '#020617', borderRadius: '8px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '8px' }}>
                    {leftPhoto ? (
                      <img src={URL.createObjectURL(leftPhoto)} alt="Left" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <Camera size={24} color="#64748b" />
                    )}
                  </div>
                  <button type="button" className="btn btn-secondary" style={{ width: '100%', padding: '6px', fontSize: '0.75rem' }} onClick={() => startCamera('left')}>
                    {leftPhoto ? "Re-Capture" : "Capture Left"}
                  </button>
                </div>

                {/* 3. Right Angle */}
                <div className="glass-panel" style={{ padding: '12px', textAlign: 'center', border: rightPhoto ? '2px solid #818cf8' : '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '8px' }}>3. Right (20°)</div>
                  <div style={{ width: '100%', height: '90px', background: '#020617', borderRadius: '8px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '8px' }}>
                    {rightPhoto ? (
                      <img src={URL.createObjectURL(rightPhoto)} alt="Right" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <Camera size={24} color="#64748b" />
                    )}
                  </div>
                  <button type="button" className="btn btn-secondary" style={{ width: '100%', padding: '6px', fontSize: '0.75rem' }} onClick={() => startCamera('right')}>
                    {rightPhoto ? "Re-Capture" : "Capture Right"}
                  </button>
                </div>

              </div>

              {/* Webcam Live Capture Popup */}
              {isCapturing && (
                <div className="glass-panel" style={{ padding: '14px', background: '#020617', border: '1px solid #38bdf8' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8', marginBottom: '8px' }}>
                    Capturing: {activeAngleTarget.toUpperCase()} Angle
                  </div>
                  <video ref={videoRef} autoPlay playsInline style={{ width: '100%', borderRadius: '8px', marginBottom: '10px' }} />
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button type="button" className="btn btn-success" style={{ flex: 1 }} onClick={capturePhoto}>
                      Snap Photo
                    </button>
                    <button type="button" className="btn btn-danger" onClick={() => setIsCapturing(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              <div style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.5 }}>
                💡 <b>Multi-template tip:</b> Capturing front, left, and right face angles allows the gate CCTV camera to recognize students even when they turn their heads or walk in crowds!
              </div>
            </div>

          </form>
        </div>
      )}

      {/* Mode 2: Bulk ZIP Importer */}
      {enrollMode === 'bulk' && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <form onSubmit={handleBulkUpload} style={{ maxWidth: '600px', margin: '0 auto' }}>
            <h3 className="font-heading" style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '12px', textAlign: 'center' }}>
              Bulk Student Batch Importer
            </h3>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', textAlign: 'center', marginBottom: '20px' }}>
              Upload a ZIP file of images named <code>RollNo_Name.jpg</code> (e.g. <code>CS101_Rahul_Sharma.jpg</code>).
            </p>

            <div className="form-group">
              <label className="form-label">Select ZIP File</label>
              <input 
                type="file" 
                accept=".zip" 
                className="form-input" 
                onChange={(e) => setBulkZipFile(e.target.files[0])}
                required
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div className="form-group">
                <label className="form-label">Default Department</label>
                <select className="form-select" value={department} onChange={(e) => setDepartment(e.target.value)}>
                  {departments.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Default Role</label>
                <select className="form-select" value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="student">Student</option>
                  <option value="faculty">Faculty</option>
                </select>
              </div>
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }} disabled={loading}>
              <Upload size={16} />
              <span>{loading ? "Processing Batch ZIP Archive..." : "Start Bulk Face Vectorization"}</span>
            </button>

            {bulkProgress && (
              <div className="glass-panel" style={{ marginTop: '20px', padding: '16px' }}>
                <h4 style={{ fontWeight: 600, color: '#10b981', marginBottom: '8px' }}>Batch Import Complete!</h4>
                <div style={{ fontSize: '0.85rem' }}>
                  <div>Successfully Enrolled: <b>{bulkProgress.enrolled_count}</b></div>
                  <div>Failed / No Face: <b>{bulkProgress.failed_count}</b></div>
                </div>
              </div>
            )}
          </form>
        </div>
      )}

      {/* Enrolled Users Directory Table */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 className="font-heading" style={{ fontSize: '1.1rem', fontWeight: 600 }}>Enrolled Campus Directory</h3>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Total {usersList.length} registered profiles in biometric vector store</span>
          </div>

          <div style={{ position: 'relative', width: '280px' }}>
            <input 
              type="text" 
              className="form-input" 
              placeholder="Search enrolled profiles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ paddingLeft: '34px' }}
            />
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '12px', color: '#64748b' }} />
          </div>
        </div>

        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Profile</th>
                <th>Roll / Emp ID</th>
                <th>Full Name</th>
                <th>Role</th>
                <th>Department</th>
                <th>Templates</th>
                <th>Enrolled Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.length > 0 ? (
                filteredUsers.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#1e293b', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {u.photo_path ? (
                          <img src={`${API_BASE}${u.photo_path}`} alt={u.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        ) : (
                          <UserPlus size={18} color="#94a3b8" />
                        )}
                      </div>
                    </td>
                    <td className="font-mono" style={{ color: '#38bdf8', fontWeight: 600 }}>{u.roll_number}</td>
                    <td style={{ fontWeight: 600 }}>{u.name}</td>
                    <td>
                      <span className="badge" style={{ background: u.role === 'faculty' ? 'rgba(129, 140, 248, 0.15)' : 'rgba(255,255,255,0.05)', color: u.role === 'faculty' ? '#818cf8' : '#cbd5e1' }}>
                        {u.role.toUpperCase()}
                      </span>
                    </td>
                    <td>{u.department}</td>
                    <td>
                      <span className="badge badge-confirmed" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Layers size={12} />
                        {u.template_count || 1} Templates
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{u.created_at?.split(' ')[0]}</td>
                    <td>
                      <button 
                        className="btn btn-danger" 
                        style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        onClick={() => setDeleteConfirmUser(u)}
                        title="Delete Profile"
                      >
                        <Trash2 size={13} />
                        <span>Delete</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '30px', color: '#64748b' }}>
                    No enrolled profiles found. Use the wizard above to enroll students!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* In-App Delete Confirmation Modal (Cannot be blocked by browser) */}
      {deleteConfirmUser && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(2, 6, 23, 0.8)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div 
            className="glass-panel" 
            style={{ 
              width: '100%', 
              maxWidth: '440px', 
              padding: '26px', 
              borderRadius: '16px', 
              border: '1px solid rgba(239, 68, 68, 0.45)', 
              textAlign: 'center',
              boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(239, 68, 68, 0.2)'
            }}
          >
            <div style={{
              width: '52px',
              height: '52px',
              borderRadius: '50%',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}>
              <Trash2 size={26} color="#f87171" />
            </div>

            <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
              Delete Biometric Profile?
            </h3>
            
            <p style={{ fontSize: '0.86rem', color: '#94a3b8', marginBottom: '22px', lineHeight: 1.5 }}>
              Are you sure you want to delete <strong style={{ color: '#ffffff' }}>{deleteConfirmUser.name}</strong> (Roll: <span className="font-mono" style={{ color: '#38bdf8' }}>{deleteConfirmUser.roll_number}</span>)? This will permanently remove their face embeddings from live camera recognition.
            </p>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '8px 20px', fontSize: '0.85rem' }}
                onClick={() => setDeleteConfirmUser(null)}
                disabled={deletingId !== null}
              >
                Cancel
              </button>

              <button 
                className="btn btn-danger" 
                style={{ 
                  padding: '8px 22px', 
                  fontSize: '0.85rem', 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '6px',
                  background: '#ef4444'
                }}
                onClick={() => executeDeleteUser(deleteConfirmUser.id, deleteConfirmUser.name)}
                disabled={deletingId !== null}
              >
                {deletingId ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 size={14} />
                    <span>Confirm Delete</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
