import React, { useState, useEffect } from 'react';
import { UserX, Clock, MapPin, Eye, Trash2, RefreshCw } from 'lucide-react';
import { API_BASE } from '../config';

export default function UnknownVisitors() {
  const [visitors, setVisitors] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchUnknowns = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/unknown/`);
      if (res.ok) {
        setVisitors(await res.json());
      }
    } catch (e) {
      console.error("Error fetching unknown visitors:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnknowns();
  }, []);

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/unknown/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setVisitors(visitors.filter(v => v.id !== id));
      }
    } catch (e) {
      alert("Error deleting record: " + e.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header */}
      <div className="glass-panel" style={{ padding: '18px 22px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="font-heading" style={{ fontSize: '1.2rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserX size={20} color="#f97316" />
            Deduplicated Unknown Visitor Gallery
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Automatically tracks and groups unrecognized individuals, saving only the single clearest face snapshot.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={fetchUnknowns}>
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
          <span>Refresh Gallery</span>
        </button>
      </div>

      {/* Grid of Unknown Cards */}
      {visitors.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '16px' }}>
          {visitors.map((v) => (
            <div key={v.id} className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', borderTop: '3px solid #f97316' }}>
              
              {/* Snapshot Image */}
              <div style={{ width: '100%', height: '180px', background: '#020617', borderRadius: '8px', overflow: 'hidden', marginBottom: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {v.best_snapshot_path ? (
                  <img 
                    src={`${API_BASE}${v.best_snapshot_path}`} 
                    alt={`Unknown #${v.track_id}`} 
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                  />
                ) : (
                  <UserX size={48} color="#64748b" />
                )}
              </div>

              {/* Visitor Details */}
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span className="badge badge-unknown" style={{ fontSize: '0.8rem' }}>
                    Track #{v.track_id}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Eye size={12} /> Seen {v.seen_count}x
                  </span>
                </div>

                <div style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Clock size={12} color="#38bdf8" />
                    <span>First Seen: <b style={{ color: '#f8fafc' }}>{v.first_seen}</b></span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Clock size={12} color="#f97316" />
                    <span>Last Seen: <b style={{ color: '#f8fafc' }}>{v.last_seen}</b></span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <MapPin size={12} color="#10b981" />
                    <span>{v.gate_id || 'Main Gate'}</span>
                  </div>
                </div>
              </div>

              {/* Action */}
              <button 
                className="btn btn-danger" 
                style={{ width: '100%', padding: '6px', fontSize: '0.78rem' }}
                onClick={() => handleDelete(v.id)}
              >
                <Trash2 size={13} />
                <span>Dismiss / Delete Log</span>
              </button>

            </div>
          ))}
        </div>
      ) : (
        <div className="glass-panel" style={{ padding: '60px', textAlign: 'center', color: '#64748b' }}>
          <UserX size={48} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
          <h4 style={{ color: '#94a3b8', fontSize: '1.05rem', marginBottom: '6px' }}>No Unknown Visitors Logged</h4>
          <p style={{ fontSize: '0.82rem' }}>All individuals detected so far are verified students or faculty members.</p>
        </div>
      )}

    </div>
  );
}
