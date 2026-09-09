import React, { useState, useEffect } from 'react';
import { 
  Download, 
  Search, 
  Filter, 
  Calendar, 
  CheckCircle2, 
  XCircle, 
  FileSpreadsheet,
  RefreshCw,
  UserCheck,
  UserX,
  Footprints,
  Clock,
  MapPin,
  X
} from 'lucide-react';
import { API_BASE } from '../config';

export default function AttendanceReport() {
  const [activeTab, setActiveTab] = useState('present'); // 'present' or 'absent'
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedDept, setSelectedDept] = useState('All');
  const [selectedRole, setSelectedRole] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  
  const [presentList, setPresentList] = useState([]);
  const [absentList, setAbsentList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewingTrail, setViewingTrail] = useState(null);

  const departments = ['All', 'Computer Science', 'Mechanical', 'Electrical', 'Civil', 'Electronics', 'Information Tech', 'Management / MBA'];

  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Present Records
      const pRes = await fetch(`${API_BASE}/api/attendance/present?date=${selectedDate}&department=${selectedDept}&role=${selectedRole}`);
      if (pRes.ok) {
        setPresentList(await pRes.json());
      }

      // 2. Fetch Absent Records
      const aRes = await fetch(`${API_BASE}/api/attendance/absent?date=${selectedDate}&department=${selectedDept}&role=${selectedRole}`);
      if (aRes.ok) {
        setAbsentList(await aRes.json());
      }
    } catch (e) {
      console.error("Error fetching attendance records:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedDate, selectedDept, selectedRole]);

  // Filter with local search
  const filteredPresent = presentList.filter(item => 
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    item.roll_number.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredAbsent = absentList.filter(item => 
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    item.roll_number.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleExportExcel = () => {
    window.open(`${API_BASE}/api/attendance/export/excel?date=${selectedDate}`, '_blank');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Top Filter & Action Bar */}
      <div className="glass-panel" style={{ padding: '18px 22px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          
          {/* Tabs: Present vs Absent */}
          <div className="nav-links" style={{ padding: '3px' }}>
            <button 
              className={`nav-item ${activeTab === 'present' ? 'active' : ''}`}
              onClick={() => setActiveTab('present')}
            >
              <UserCheck size={16} color={activeTab === 'present' ? '#10b981' : '#94a3b8'} />
              <span>Present List ({presentList.length})</span>
            </button>

            <button 
              className={`nav-item ${activeTab === 'absent' ? 'active' : ''}`}
              onClick={() => setActiveTab('absent')}
            >
              <UserX size={16} color={activeTab === 'absent' ? '#f43f5e' : '#94a3b8'} />
              <span>Absent List ({absentList.length})</span>
            </button>
          </div>

          {/* Action Export Buttons */}
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={fetchData} title="Refresh Data">
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>

            <button className="btn btn-primary" onClick={handleExportExcel}>
              <FileSpreadsheet size={16} />
              <span>Export Full Excel Report</span>
            </button>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
          
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Select Date</label>
            <input 
              type="date" 
              className="form-input"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Department</label>
            <select 
              className="form-select"
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
            >
              {departments.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Role</label>
            <select 
              className="form-select"
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
            >
              <option value="All">All Roles</option>
              <option value="student">Students Only</option>
              <option value="faculty">Faculty Only</option>
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Search Person</label>
            <div style={{ position: 'relative' }}>
              <input 
                type="text" 
                className="form-input" 
                placeholder="Search by Name or Roll No..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ paddingLeft: '34px' }}
              />
              <Search size={16} style={{ position: 'absolute', left: '10px', top: '12px', color: '#64748b' }} />
            </div>
          </div>

        </div>
      </div>

      {/* Main Table View */}
      <div className="glass-panel" style={{ padding: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h3 className="font-heading" style={{ fontSize: '1.05rem', fontWeight: 600 }}>
            {activeTab === 'present' ? `Present Today (${filteredPresent.length} Records)` : `Absent Today (${filteredAbsent.length} Records)`}
          </h3>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Showing records for {selectedDate}</span>
        </div>

        {activeTab === 'present' ? (
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Roll / Emp No</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Department</th>
                  <th>Entered Campus</th>
                  <th>Last Seen</th>
                  <th>Footprint</th>
                  <th>Status</th>
                  <th>Audit Trail</th>
                </tr>
              </thead>
              <tbody>
                {filteredPresent.length > 0 ? (
                  filteredPresent.map((row) => (
                    <tr key={row.id}>
                      <td className="font-mono" style={{ color: '#38bdf8', fontWeight: 600 }}>{row.roll_number}</td>
                      <td style={{ fontWeight: 600 }}>{row.name}</td>
                      <td>
                        <span className="badge" style={{ background: row.role === 'faculty' ? 'rgba(129, 140, 248, 0.15)' : 'rgba(255,255,255,0.05)', color: row.role === 'faculty' ? '#818cf8' : '#cbd5e1' }}>
                          {row.role.toUpperCase()}
                        </span>
                      </td>
                      <td>{row.department}</td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', fontSize: '0.78rem' }}>
                          <span className="font-mono" style={{ color: '#10b981', fontWeight: 600 }}>{row.first_seen || row.time}</span>
                          <span style={{ color: '#64748b', fontSize: '0.7rem' }}>{row.entry_gate || row.gate_id || 'Main Gate'}</span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', fontSize: '0.78rem' }}>
                          <span className="font-mono" style={{ color: '#38bdf8', fontWeight: 600 }}>{row.last_seen || row.time}</span>
                          <span style={{ color: '#64748b', fontSize: '0.7rem' }}>{row.last_gate || row.gate_id || 'Main Gate'}</span>
                        </div>
                      </td>
                      <td>
                        <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.12)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <Footprints size={12} />
                          <span>{row.seen_count || 1} {row.seen_count === 1 ? 'capture' : 'captures'}</span>
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${row.status === 'Late' ? 'badge-late' : 'badge-present'}`}>
                          {row.status}
                        </span>
                      </td>
                      <td>
                        <button 
                          className="btn btn-secondary"
                          style={{ padding: '3px 8px', fontSize: '0.7rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                          onClick={() => setViewingTrail(row)}
                          title="View complete campus movement breadcrumb trail"
                        >
                          <Footprints size={12} color="#38bdf8" />
                          <span>View Trail</span>
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="9" style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>
                      No present records found matching criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Roll / Emp No</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Department</th>
                  <th>Year</th>
                  <th>Email</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredAbsent.length > 0 ? (
                  filteredAbsent.map((row) => (
                    <tr key={row.id}>
                      <td className="font-mono" style={{ color: '#f43f5e', fontWeight: 600 }}>{row.roll_number}</td>
                      <td style={{ fontWeight: 600 }}>{row.name}</td>
                      <td>
                        <span className="badge" style={{ background: row.role === 'faculty' ? 'rgba(129, 140, 248, 0.15)' : 'rgba(255,255,255,0.05)', color: row.role === 'faculty' ? '#818cf8' : '#cbd5e1' }}>
                          {row.role.toUpperCase()}
                        </span>
                      </td>
                      <td>{row.department}</td>
                      <td>{row.year || 'N/A'}</td>
                      <td>{row.email || 'N/A'}</td>
                      <td>
                        <span className="badge badge-absent">ABSENT</span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: '#10b981' }}>
                      🎉 Zero absentees! 100% attendance recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footprint Trail Modal */}
      {viewingTrail && (
        <div className="modal-backdrop">
          <div className="modal-dialog" style={{ maxWidth: '520px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Footprints size={20} color="#a855f7" />
                <h3 className="font-heading" style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                  Campus Footprint Trail
                </h3>
              </div>
              <button 
                onClick={() => setViewingTrail(null)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', marginBottom: '16px' }}>
              <div style={{ fontWeight: 600, fontSize: '0.95rem', color: '#f8fafc' }}>
                {viewingTrail.name}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                {viewingTrail.roll_number} • {viewingTrail.department} • {viewingTrail.role?.toUpperCase()}
              </div>
              <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '0.75rem' }}>
                <span>Entered: <strong className="font-mono" style={{ color: '#10b981' }}>{viewingTrail.first_seen || viewingTrail.time}</strong></span>
                <span>Last Seen: <strong className="font-mono" style={{ color: '#38bdf8' }}>{viewingTrail.last_seen || viewingTrail.time}</strong></span>
                <span>Sightings: <strong>{viewingTrail.seen_count || 1}</strong></span>
              </div>
            </div>

            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '10px' }}>
              Movement Chronology ({viewingTrail.trail?.length || 1} Checkpoints):
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto', paddingRight: '4px' }}>
              {viewingTrail.trail && viewingTrail.trail.length > 0 ? (
                viewingTrail.trail.map((pt, idx) => (
                  <div 
                    key={idx} 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      background: 'rgba(0, 0, 0, 0.25)',
                      borderRadius: '6px',
                      borderLeft: `3px solid ${idx === 0 ? '#10b981' : (idx === viewingTrail.trail.length - 1 ? '#38bdf8' : '#a855f7')}`
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="font-mono" style={{ color: '#cbd5e1', fontSize: '0.8rem', fontWeight: 600 }}>{pt.time}</span>
                      <span style={{ color: '#64748b' }}>•</span>
                      <span style={{ color: '#f1f5f9', fontSize: '0.8rem' }}>{pt.gate}</span>
                    </div>
                    <span className="badge" style={{ fontSize: '0.65rem' }}>
                      {pt.type || 'Detection'}
                    </span>
                  </div>
                ))
              ) : (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  background: 'rgba(0, 0, 0, 0.25)',
                  borderRadius: '6px',
                  borderLeft: '3px solid #10b981'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="font-mono" style={{ color: '#cbd5e1', fontSize: '0.8rem', fontWeight: 600 }}>{viewingTrail.first_seen || viewingTrail.time}</span>
                    <span style={{ color: '#64748b' }}>•</span>
                    <span style={{ color: '#f1f5f9', fontSize: '0.8rem' }}>{viewingTrail.entry_gate || viewingTrail.gate_id || 'Main Gate'}</span>
                  </div>
                  <span className="badge badge-present" style={{ fontSize: '0.65rem' }}>Entry</span>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button className="btn btn-secondary" onClick={() => setViewingTrail(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
