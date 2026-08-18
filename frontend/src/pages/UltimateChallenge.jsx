import { useState, useEffect } from 'react';
import { getTeamUC } from '../api';
import TeamSelector from '../components/TeamSelector';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

function getColor(acc) {
  if (acc >= 0.65) return 'var(--green)';
  if (acc >= 0.40) return 'var(--yellow)';
  return 'var(--red)';
}

export default function UltimateChallenge() {
  const [teamId, setTeamId]     = useState(null);
  const [oppId, setOppId]       = useState(null);
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(false);

  useEffect(() => {
    if (!teamId) return;
    setLoading(true);
    getTeamUC(teamId, oppId)
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [teamId, oppId]);

  const categories = data?.stats?.sorted_by_accuracy || [];
  const chartData  = categories.map(c => ({
    cat: c.category.length > 16 ? c.category.slice(0, 14) + '…' : c.category,
    acc: Math.round(c.avg_accuracy * 100),
    avg_pts: Math.round(c.avg_points_per_game),
    times: c.times_selected,
  }));

  const rec = data?.recommendation?.recommendation;

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Ultimate Challenge</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 24 }}>
        60 seconds · 10 questions · 50 pts each · 500 pts max. Category strategy and performance analysis.
      </p>

      <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' }}>
        <TeamSelector value={teamId} onChange={setTeamId} label="Your team" />
        <TeamSelector value={oppId}  onChange={setOppId}  label="Opponent (optional)" />
      </div>

      {loading && <div className="loading">Loading UC analysis…</div>}

      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Recommendation card */}
          {rec && (
            <div className="card" style={{ background: 'var(--green-soft)', border: '1px solid var(--green)' }}>
              <div style={{ fontSize: 12, color: 'var(--green)', fontWeight: 700, marginBottom: 8 }}>
                ⭐ RECOMMENDED UC CATEGORY
              </div>
              <div style={{ fontSize: 22, fontWeight: 800 }}>{rec.category}</div>
              <div style={{ color: 'var(--muted)', marginTop: 6, fontSize: 13 }}>
                {data.recommendation.reason}
              </div>
              <div style={{ display: 'flex', gap: 24, marginTop: 14 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Your accuracy</div>
                  <div style={{ fontWeight: 700, color: 'var(--green)', fontSize: 18 }}>
                    {(rec.your_accuracy * 100).toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--muted)' }}>Avg pts/game</div>
                  <div style={{ fontWeight: 700, color: 'var(--accent)', fontSize: 18 }}>
                    {rec.your_avg_points.toFixed(0)}
                  </div>
                </div>
                {rec.opponent_accuracy !== null && (
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>Opp accuracy</div>
                    <div style={{ fontWeight: 700, color: 'var(--red)', fontSize: 18 }}>
                      {(rec.opponent_accuracy * 100).toFixed(1)}%
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Accuracy by category chart */}
          {chartData.length > 0 && (
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 16 }}>UC Accuracy by Category</div>
              <ResponsiveContainer width="100%" height={Math.max(180, chartData.length * 36)}>
                <BarChart data={chartData} layout="vertical">
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 11 }} tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="cat" tick={{ fill: 'var(--text)', fontSize: 11 }} width={150} />
                  <Tooltip
                    contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 12 }}
                    formatter={(v, name) => name === 'acc' ? [`${v}%`, 'Accuracy'] : [v, 'Avg Pts']}
                  />
                  <Bar dataKey="acc" radius={[0, 4, 4, 0]} name="acc">
                    {chartData.map((e, i) => <Cell key={i} fill={getColor(e.acc / 100)} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* All options table */}
          {data.recommendation?.all_options?.length > 0 && (
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 12 }}>All Category Options (Ranked)</div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ color: 'var(--muted)', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                    <th style={{ padding: '6px 8px' }}>Category</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right' }}>Your Acc.</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right' }}>Times Picked</th>
                    {oppId && <th style={{ padding: '6px 8px', textAlign: 'right' }}>Opp Acc.</th>}
                    <th style={{ padding: '6px 8px', textAlign: 'right' }}>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recommendation.all_options.map((opt, i) => {
                    const color = getColor(opt.your_accuracy);
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '8px 8px' }}>{opt.category}</td>
                        <td style={{ padding: '8px 8px', textAlign: 'right', color, fontWeight: 700 }}>
                          {(opt.your_accuracy * 100).toFixed(1)}%
                        </td>
                        <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--muted)' }}>
                          {opt.times_selected}×
                        </td>
                        {oppId && (
                          <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--muted)' }}>
                            {opt.opponent_accuracy !== null
                              ? <>
                                  {(opt.opponent_accuracy * 100).toFixed(1)}%
                                  <span style={{ fontSize: 11, opacity: 0.6 }}> ({opt.opponent_times_selected}×)</span>
                                </>
                              : '—'}
                          </td>
                        )}
                        <td style={{ padding: '8px 8px', textAlign: 'right', fontWeight: 700, color: 'var(--accent)' }}>
                          {(opt.recommendation_score * 100).toFixed(1)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* History */}
          {data.history?.length > 0 && (
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 12 }}>UC History</div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ color: 'var(--muted)', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                    <th style={{ padding: '6px 8px' }}>Game</th>
                    <th style={{ padding: '6px 8px' }}>Category</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right' }}>Pts</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right' }}>Correct</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right' }}>Accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {data.history.map((h, i) => {
                    const color = getColor(h.accuracy);
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '8px 8px', color: 'var(--muted)' }}>Rm{h.room} Gm{h.game}</td>
                        <td style={{ padding: '8px 8px' }}>{h.category}</td>
                        <td style={{ padding: '8px 8px', textAlign: 'right', fontWeight: 700 }}>{h.points_scored}</td>
                        <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--muted)' }}>{h.questions_correct}/10</td>
                        <td style={{ padding: '8px 8px', textAlign: 'right', color, fontWeight: 700 }}>{(h.accuracy * 100).toFixed(0)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {!teamId && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: 60, color: 'var(--muted)' }}>
          Select a team to view Ultimate Challenge analysis.
        </div>
      )}
    </div>
  );
}
