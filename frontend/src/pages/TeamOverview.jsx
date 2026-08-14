import { useState, useEffect } from 'react';
import { getTeamOverview, uploadPDF } from '../api';
import TeamSelector from '../components/TeamSelector';
import CategoryHeatmap from '../components/CategoryHeatmap';
import StrengthBar from '../components/StrengthBar';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function TeamOverview() {
  const [teamId, setTeamId] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');

  useEffect(() => {
    if (!teamId) return;
    setLoading(true);
    getTeamOverview(teamId)
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [teamId]);

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg('');
    try {
      const res = await uploadPDF(file);
      setUploadMsg(`✓ Uploaded: ${res.data.type}`);
      // Refresh if same team is loaded
      if (teamId) {
        const r = await getTeamOverview(teamId);
        setData(r.data);
      }
    } catch {
      setUploadMsg('✗ Upload failed');
    }
    setUploading(false);
  }

  // Build radar data from top categories
  const radarData = data
    ? Object.entries(data.category_coverage || {})
        .sort((a, b) => b[1].best_accuracy - a[1].best_accuracy)
        .slice(0, 8)
        .map(([cat, v]) => ({ cat: cat.length > 14 ? cat.slice(0, 12) + '…' : cat, value: Math.round(v.best_accuracy * 100) }))
    : [];

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Team Overview</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 24 }}>
        Overall strength, category coverage heatmap, and key metrics.
      </p>

      {/* Upload + Team select row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap', alignItems: 'center' }}>
        <TeamSelector value={teamId} onChange={setTeamId} />
        <label style={{
          background: 'var(--surface2)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
        }}>
          {uploading ? 'Uploading…' : '+ Upload PDF'}
          <input type="file" accept=".pdf" style={{ display: 'none' }} onChange={handleUpload} />
        </label>
        {uploadMsg && <span style={{ color: uploadMsg.startsWith('✓') ? 'var(--green)' : 'var(--red)', fontSize: 13 }}>{uploadMsg}</span>}
      </div>

      {loading && <div className="loading">Loading…</div>}

      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Top stat cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
            {[
              { label: 'Overall Strength', value: `${(data.overall_strength * 100).toFixed(1)}%`, sub: 'avg best-per-category' },
              { label: 'Record', value: `${data.wins}W – ${data.losses}L`, sub: 'round robin' },
              { label: 'Points Scored', value: (data.total_points || 0).toLocaleString(), sub: 'total' },
              { label: 'Players', value: (data.players || []).length, sub: 'on roster' },
            ].map(s => (
              <div key={s.label} className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--accent)' }}>{s.value}</div>
                <div style={{ fontSize: 12, fontWeight: 600, marginTop: 4 }}>{s.label}</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{s.sub}</div>
              </div>
            ))}
          </div>

          {/* Radar + players side by side */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 16 }}>Top Categories (Radar)</div>
              <ResponsiveContainer width="100%" height={250}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#2e3350" />
                  <PolarAngleAxis dataKey="cat" tick={{ fill: '#8892a4', fontSize: 11 }} />
                  <Radar dataKey="value" stroke="#4f8ef7" fill="#4f8ef7" fillOpacity={0.25} />
                  <Tooltip contentStyle={{ background: '#1a1d27', border: '1px solid #2e3350' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 16 }}>Roster Strength</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {(data.players || []).map(p => (
                  <div key={p.id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600 }}>{p.name}</span>
                      <span style={{ color: 'var(--muted)', fontSize: 12 }}>{(p.overall_strength * 100).toFixed(0)}%</span>
                    </div>
                    <StrengthBar value={p.overall_strength} showLabel={false} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Strengths / Gaps */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 12, color: 'var(--green)' }}>💪 Top Categories</div>
              {(data.top_categories || []).map(c => (
                <div key={c.category} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                  <span>{c.category}</span>
                  <span style={{ color: 'var(--green)', fontWeight: 700 }}>{(c.accuracy * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 12, color: 'var(--red)' }}>⚠️ Coverage Gaps</div>
              {(data.weak_categories || []).length === 0
                ? <div style={{ color: 'var(--muted)' }}>No significant gaps.</div>
                : (data.weak_categories || []).map(c => (
                  <div key={c.category} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <span>{c.category}</span>
                    <span style={{ color: 'var(--red)', fontWeight: 700 }}>{(c.accuracy * 100).toFixed(0)}%</span>
                  </div>
                ))
              }
            </div>
          </div>

          {/* Full heatmap */}
          <div className="card">
            <div style={{ fontWeight: 700, marginBottom: 16 }}>Category Coverage Heatmap</div>
            <CategoryHeatmap coverage={data.category_coverage} />
          </div>

        </div>
      )}

      {!teamId && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: 60, color: 'var(--muted)' }}>
          Select a team above to view their analysis.
        </div>
      )}
    </div>
  );
}
