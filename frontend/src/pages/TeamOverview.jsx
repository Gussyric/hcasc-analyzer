import { useState, useEffect } from 'react';
import { getTeamOverview, uploadPDF, getTournaments } from '../api';
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
  const [tournaments, setTournaments] = useState([]);
  const [uploadTournamentId, setUploadTournamentId] = useState('');
  const [viewTournamentId, setViewTournamentId] = useState('');

  useEffect(() => {
    if (!teamId) { setData(null); return; }
    setLoading(true);
    getTeamOverview(teamId, viewTournamentId || null)
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [teamId, viewTournamentId]);

  useEffect(() => {
    getTournaments().then(r => setTournaments(r.data)).catch(() => {});
  }, []);

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg('');
    try {
      const res = await uploadPDF(file, uploadTournamentId || null);
      setUploadMsg(`✓ Uploaded: ${res.data.type}`);
      // Refresh if same team is loaded
      if (teamId) {
        const r = await getTeamOverview(teamId, viewTournamentId || null);
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
      <div style={{ display: 'flex', gap: 12, marginBottom: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <TeamSelector value={teamId} onChange={setTeamId} tournamentId={viewTournamentId || null} />
        <select
          value={viewTournamentId}
          onChange={e => setViewTournamentId(e.target.value)}
          title="Scope the stats below to one tournament instead of the team's all-time aggregate"
          style={{
            background: 'var(--surface2)', border: '1px solid var(--accent)',
            borderRadius: 8, padding: '8px 12px', fontSize: 13, color: 'var(--text)',
          }}
        >
          <option value="">Viewing: All Tournaments</option>
          {tournaments.map(t => (
            <option key={t.id} value={t.id}>Viewing: {t.name}</option>
          ))}
        </select>
        <label style={{
          background: 'var(--surface2)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
        }}>
          {uploading ? 'Uploading…' : '+ Upload PDF'}
          <input type="file" accept=".pdf" style={{ display: 'none' }} onChange={handleUpload} />
        </label>
      </div>

      {/* Upload-tagging row — separate from the view filter above */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 28, alignItems: 'center' }}>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>Tag next upload to:</span>
        <select
          value={uploadTournamentId}
          onChange={e => setUploadTournamentId(e.target.value)}
          title="Which tournament the next uploaded PDF gets attached to"
          style={{
            background: 'var(--surface2)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '6px 10px', fontSize: 12, color: 'var(--text)',
          }}
        >
          <option value="">No tournament (untagged)</option>
          {tournaments.map(t => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        {uploadMsg && <span style={{ color: uploadMsg.startsWith('✓') ? 'var(--green)' : 'var(--red)', fontSize: 13 }}>{uploadMsg}</span>}
      </div>

      {loading && <div className="loading">Loading…</div>}

      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Top stat cards */}
          {(() => {
            const poW = data.playoff_wins || 0;
            const poL = data.playoff_losses || 0;
            const hasPlayoffs = poW + poL > 0;
            // wins/losses/total_points from the API are already the combined
            // (round-robin + playoffs) total — round_robin_* fields exist
            // separately just for the breakdown text below.
            const recordSub = hasPlayoffs
              ? `${data.round_robin_wins}-${data.round_robin_losses} RR, ${poW}-${poL} playoffs`
              : 'round robin';
            const pointsSub = hasPlayoffs ? 'total (RR + playoffs)' : 'round robin';
            const totalPoints = (data.total_points || 0) + (data.playoff_points_for || 0);
            return (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
            {[
              { label: 'Overall Strength', value: `${(data.overall_strength * 100).toFixed(1)}%`, sub: 'categories + UC, weighted' },
              { label: 'Record', value: `${data.wins}W – ${data.losses}L`, sub: recordSub },
              { label: 'Points Scored', value: totalPoints.toLocaleString(), sub: pointsSub },
              { label: 'Players', value: (data.players || []).length, sub: 'on roster' },
            ].map(s => (
              <div key={s.label} className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--accent)' }}>{s.value}</div>
                <div style={{ fontSize: 12, fontWeight: 600, marginTop: 4 }}>{s.label}</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{s.sub}</div>
              </div>
            ))}
          </div>
            );
          })()}

          {/* Radar + players side by side */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 16 }}>Top Categories (Radar)</div>
              <ResponsiveContainer width="100%" height={250}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="cat" tick={{ fill: 'var(--muted)', fontSize: 11 }} />
                  <Radar dataKey="value" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.25} />
                  <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)' }} />
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
