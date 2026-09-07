import React, { useState, useEffect } from 'react';
import { Sliders, Activity, ShieldCheck, Target, RefreshCw, Info } from 'lucide-react';

export default function Calibration() {
  const [rocData, setRocData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentThreshold, setCurrentThreshold] = useState(0.60);

  const fetchCalibration = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/calibration/evaluate');
      if (res.ok) {
        const data = await res.json();
        setRocData(data);
        if (data.recommended_threshold) {
          setCurrentThreshold(data.recommended_threshold);
        }
      }
    } catch (e) {
      console.error("Error evaluating ROC:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCalibration();
  }, []);

  const handleApplyThreshold = async (thresholdVal) => {
    try {
      const res = await fetch('http://localhost:8000/api/camera/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ similarity_threshold: thresholdVal })
      });
      if (res.ok) {
        alert(`Successfully applied similarity threshold: ${thresholdVal}`);
      }
    } catch (e) {
      alert("Error applying threshold: " + e.message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header */}
      <div className="glass-panel" style={{ padding: '18px 22px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="font-heading" style={{ fontSize: '1.2rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={20} color="#38bdf8" />
            Empirical Threshold Calibration & ROC Analysis
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Calculates False Acceptance Rate (FAR) vs False Rejection Rate (FRR) across enrolled dataset profiles.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={fetchCalibration}>
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
          <span>Re-Calibrate ROC</span>
        </button>
      </div>

      {rocData && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(300px, 1fr)', gap: '20px' }}>
          
          {/* Left: Interactive Threshold Table & Curve */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h3 className="font-heading" style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '14px' }}>
              ROC Curve Evaluation Table
            </h3>

            <div className="table-container" style={{ maxHeight: '420px' }}>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Threshold (θ)</th>
                    <th>False Accept (FAR %)</th>
                    <th>False Reject (FRR %)</th>
                    <th>Overall Accuracy</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {rocData.roc_curve && rocData.roc_curve.map((point) => {
                    const isRecommended = point.threshold === rocData.recommended_threshold;
                    return (
                      <tr key={point.threshold} style={{ background: isRecommended ? 'rgba(56, 189, 248, 0.08)' : 'transparent' }}>
                        <td className="font-mono" style={{ fontWeight: 600, color: isRecommended ? '#38bdf8' : '#f8fafc' }}>
                          {point.threshold.toFixed(2)} {isRecommended && '⭐ (Optimal)'}
                        </td>
                        <td className="font-mono" style={{ color: '#f43f5e' }}>{point.far}%</td>
                        <td className="font-mono" style={{ color: '#f59e0b' }}>{point.frr}%</td>
                        <td className="font-mono" style={{ color: '#10b981', fontWeight: 600 }}>{point.accuracy}%</td>
                        <td>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                            onClick={() => {
                              setCurrentThreshold(point.threshold);
                              handleApplyThreshold(point.threshold);
                            }}
                          >
                            Set {point.threshold.toFixed(2)}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right: Recommendation & Operating Point Card */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            <div className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid #10b981' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <Target size={20} color="#10b981" />
                <h4 style={{ fontWeight: 600, color: '#10b981' }}>Recommended Operating Threshold</h4>
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: '#f8fafc', marginBottom: '6px' }}>
                θ = {rocData.recommended_threshold}
              </div>
              <div style={{ fontSize: '0.82rem', color: '#94a3b8', lineHeight: 1.5, marginBottom: '14px' }}>
                {rocData.recommended_reason}
              </div>

              <button 
                className="btn btn-success" 
                style={{ width: '100%' }}
                onClick={() => handleApplyThreshold(rocData.recommended_threshold)}
              >
                Apply Recommended Threshold
              </button>
            </div>

            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <Info size={18} color="#38bdf8" />
                <h4 style={{ fontWeight: 600 }}>Calibration Guide</h4>
              </div>
              
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.6, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>
                  <b style={{ color: '#f8fafc' }}>High-Security Gate:</b> Set threshold higher (<b>0.65 – 0.72</b>) to minimize stranger impostor entry.
                </div>
                <div>
                  <b style={{ color: '#f8fafc' }}>High-Throughput Crowd Gate:</b> Set threshold around (<b>0.55 – 0.60</b>) with 3-frame temporal confirmation to prevent bottlenecks during morning rush hour.
                </div>
                <div>
                  <b style={{ color: '#f8fafc' }}>Dataset Evaluated:</b> {rocData.enrolled_templates_count} active face templates in database.
                </div>
              </div>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}
