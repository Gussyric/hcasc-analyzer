import { useState, useEffect } from 'react';
import { getMatchup } from '../api';
import TeamSelector from '../components/TeamSelector';
import StrengthBar from '../components/StrengthBar';

function AdvBadge({ adv, t1, t2 }) {
  if (adv === 'team1') return <span style={{ color: 'var(--accent)', fontWeight: 700, fontSize: 12 }}>← {t1}</span>;
  if (adv === 'team2') return <span style={{ color: 'var(--gold)', fontWeight: 700, fontSize: 12 }}>{t2} →</span>;
  return <span style={{ color: 'var(--muted)', fontSize: 12 }}>Even</span>;
}

export default function HeadToHead() {
  const [t1Id, setT1Id] = useState(null);
  const [t2Id, setT2Id] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (!t1Id || !t2Id || t1Id === t2Id) return;
    setLoading(true);
    getMatchup(t1Id, t2Id)
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [t1Id, t2Id]);

  const t1 = data?.team1;
  const t2 = data?.team2;

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Head-to-Head Matchup</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 24 }}>
        Team vs team comparison, player matchups, UC advantage, and scouting report.
      </p>

      <div style={{ display: 'flex', gap: 12, marginBottom: 28 }}>
        <TeamSelector value={t1Id} onChange={setT1Id} label="Team 1" />
        <TeamSelector value={t2Id} onChange={setT2Id} label="Team 2" />
      </div>

      {loading && <div className="loading">Running matchup analysis…</div>}

      {t1Id && t2Id && t1Id === t2Id && (
        <div className="error">Select two different teams.</div>
      )}

      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Team comparison header */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 16, alignItems: 'center' }}>
            <div className="card" style={{ textAlign: 'center', border: '1px solid var(--accent)' }}>
              <div style={{ fontSize: 18, fontWeight: 800 }}>{t1.name}</div>
              <div style={{ fontSize: 28, fontWeight: 900, color: 'var(--accent)', margin: '8px 0' }}>
                {(t1.overall_strength * 100).toFixed(1)}%
              </div>
              <div style={{ color: 'var(--muted)', fontSize: 13 }}>{t1.wins}W – {t1.losses}L</div>
              <StrengthBar value={t1.overall_strength} />
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 900, color: 'var(--muted)' }}>VS</div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                {data.category_advantages.team1}–{data.category_advantages.team2} cats
              </div>
              <div style={{ fontSize: 10, color: 'var(--muted)', opacity: 0.7 }}>
                of {data.category_advantages.team1 + data.category_advantages.team2 + data.category_advantages.even} both played
              </div>
            </div>
            <div className="card" style={{ textAlign: 'center', border: '1px solid var(--gold)' }}>
              <div style={{ fontSize: 18, fontWeight: 800 }}>{t2.name}</div>
              <div style={{ fontSize: 28, fontWeight: 900, color: 'var(--gold)', margin: '8px 0' }}>
                {(t2.overall_strength * 100).toFixed(1)}%
              </div>
              <div style={{ color: 'var(--muted)', fontSize: 13 }}>{t2.wins}W – {t2.losses}L</div>
              <StrengthBar value={t2.overall_strength} />
            </div>
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 8 }}>
            {['overview', 'categories', 'players', 'uc'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={activeTab === tab ? 'primary' : 'ghost'}
                style={{ textTransform: 'capitalize' }}
              >
                {tab === 'uc' ? 'Ultimate Challenge' : tab}
              </button>
            ))}
          </div>

          {/* Overview tab: scouting report */}
          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="card">
                <div style={{ fontWeight: 700, marginBottom: 14 }}>🔍 Scouting Report</div>
                {data.scouting_report.map((line, i) => (
                  <div key={i} style={{
                    padding: '10px 14px', marginBottom: 8,
                    background: 'var(--surface2)', borderRadius: 8, fontSize: 13,
                  }}>
                    {line}
                  </div>
                ))}
              </div>
              {data.historical_matchups?.length > 0 && (
                <div className="card">
                  <div style={{ fontWeight: 700, marginBottom: 12 }}>Historical Games</div>
                  {data.historical_matchups.map((g, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                      <span style={{ color: 'var(--muted)' }}>Rm{g.room} Gm{g.game}</span>
                      <span style={{ fontWeight: 600 }}>{g.team1} <span style={{ color: 'var(--accent)' }}>{g.team1_score}</span></span>
                      <span style={{ color: 'var(--muted)' }}>vs</span>
                      <span style={{ fontWeight: 600 }}><span style={{ color: 'var(--gold)' }}>{g.team2_score}</span> {g.team2}</span>
                      <span style={{ color: 'var(--green)', fontSize: 12 }}>↑ {g.winner}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Categories tab */}
          {activeTab === 'categories' && (
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 12 }}>Category-by-Category Comparison</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px 1fr', gap: 4, fontSize: 12 }}>
                <div style={{ color: 'var(--accent)', fontWeight: 700, padding: '6px 0' }}>{t1.name}</div>
                <div style={{ color: 'var(--muted)', textAlign: 'center', padding: '6px 0' }}>Category</div>
                <div style={{ color: 'var(--gold)', fontWeight: 700, padding: '6px 0', textAlign: 'right' }}>{t2.name}</div>
                {data.category_comparison.map((cat, i) => {
                  const oneSided = cat.advantage === 'team1_only' || cat.advantage === 'team2_only';
                  const t1color = cat.advantage === 'team1' ? 'var(--accent)' : cat.advantage === 'even' ? 'var(--muted)' : 'var(--text)';
                  const t2color = cat.advantage === 'team2' ? 'var(--gold)' : cat.advantage === 'even' ? 'var(--muted)' : 'var(--text)';
                  const dimStyle = oneSided ? { opacity: 0.45, fontStyle: 'italic' } : {};
                  return [
                    <div key={`l${i}`} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', color: t1color, fontWeight: cat.advantage === 'team1' ? 700 : 400, ...(cat.team1_accuracy === null ? dimStyle : {}) }}>
                      {cat.team1_accuracy !== null ? `${(cat.team1_accuracy * 100).toFixed(0)}%` : 'no data'}
                    </div>,
                    <div key={`c${i}`} style={{ padding: '6px 4px', borderBottom: '1px solid var(--border)', textAlign: 'center', color: 'var(--muted)', fontSize: 11 }} title={oneSided ? `Only ${cat.advantage === 'team1_only' ? t1.name : t2.name} has played this category` : undefined}>
                      {cat.category.length > 18 ? cat.category.slice(0, 16) + '…' : cat.category}
                    </div>,
                    <div key={`r${i}`} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', color: t2color, fontWeight: cat.advantage === 'team2' ? 700 : 400, textAlign: 'right', ...(cat.team2_accuracy === null ? dimStyle : {}) }}>
                      {cat.team2_accuracy !== null ? `${(cat.team2_accuracy * 100).toFixed(0)}%` : 'no data'}
                    </div>,
                  ];
                })}
              </div>
            </div>
          )}

          {/* Players tab */}
          {activeTab === 'players' && (
            <div className="card">
              <div style={{ fontWeight: 700, marginBottom: 14 }}>Player Matchups (by strength rank)</div>
              {data.player_matchups.map((m, i) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 12, alignItems: 'center', padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                  <div>
                    {m.player1 ? (
                      <>
                        <div style={{ fontWeight: 600 }}>{m.player1.name}</div>
                        <StrengthBar value={m.player1.overall_strength} />
                      </>
                    ) : <span style={{ color: 'var(--muted)' }}>—</span>}
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <AdvBadge adv={m.advantage} t1={t1.name} t2={t2.name} />
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    {m.player2 ? (
                      <>
                        <div style={{ fontWeight: 600 }}>{m.player2.name}</div>
                        <StrengthBar value={m.player2.overall_strength} />
                      </>
                    ) : <span style={{ color: 'var(--muted)' }}>—</span>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* UC tab */}
          {activeTab === 'uc' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {[
                { team: t1, rec: data.uc.team1_recommendation, reason: data.uc.team1_reason, color: 'var(--accent)', strength: data.uc.team1_uc_strength },
                { team: t2, rec: data.uc.team2_recommendation, reason: data.uc.team2_reason, color: 'var(--gold)', strength: data.uc.team2_uc_strength },
              ].map(({ team, rec, reason, color, strength }) => (
                <div key={team.name} className="card" style={{ border: `1px solid ${color}33` }}>
                  <div style={{ fontWeight: 700, color, marginBottom: 10 }}>{team.name}</div>
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 11, color: 'var(--muted)' }}>UC Strength</div>
                    <StrengthBar value={strength} />
                  </div>
                  {rec ? (
                    <>
                      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>
                        Recommended: {rec.category}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--muted)' }}>{reason}</div>
                    </>
                  ) : (
                    <div style={{ color: 'var(--muted)', fontSize: 13 }}>No UC data available.</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {(!t1Id || !t2Id) && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: 60, color: 'var(--muted)' }}>
          Select two teams to run a head-to-head analysis.
        </div>
      )}
    </div>
  );
}
