import { useState, useEffect } from 'react';
import { getTeamLineup } from '../api';
import TeamSelector from '../components/TeamSelector';
import StrengthBar from '../components/StrengthBar';

function LineupCard({ combo, isTop }) {
  const borderColor = isTop ? 'var(--green)' : 'var(--border)';
  const bg = isTop ? '#06322a' : 'var(--surface)';

  return (
    <div className="card" style={{ border: `1px solid ${borderColor}`, background: bg }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            background: isTop ? 'var(--green)' : 'var(--surface2)',
            color: isTop ? '#000' : 'var(--muted)',
            fontWeight: 800, fontSize: 13,
            borderRadius: 6, padding: '2px 10px',
          }}>
            #{combo.rank}
          </span>
          {isTop && <span style={{ color: 'var(--green)', fontSize: 12, fontWeight: 600 }}>⭐ RECOMMENDED</span>}
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 20, fontWeight: 800, color: isTop ? 'var(--green)' : 'var(--accent)' }}>
            {(combo.overall_score * 100).toFixed(1)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>lineup score</div>
        </div>
      </div>

      {/* Players */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        {combo.players.map(p => (
          <div key={p.id} style={{
            background: 'var(--surface2)', borderRadius: 8,
            padding: '6px 12px', fontSize: 13, fontWeight: 600,
          }}>
            {p.name}
            <span style={{ color: 'var(--muted)', fontWeight: 400, marginLeft: 6 }}>
              {(p.overall_strength * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>

      {/* Sub scores */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 14 }}>
        {[
          { label: 'Coverage', value: combo.coverage_score },
          { label: 'Strength', value: combo.combined_strength },
        ].map(m => (
          <div key={m.label}>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>{m.label}</div>
            <StrengthBar value={m.value} />
          </div>
        ))}
        <div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Cats Covered</div>
          <div style={{ fontWeight: 700, color: 'var(--accent)' }}>
            {combo.categories_covered} / {combo.total_categories}
          </div>
        </div>
      </div>

      {/* Bench */}
      <div style={{ fontSize: 12, color: 'var(--muted)' }}>
        Bench: <strong style={{ color: 'var(--text)' }}>{combo.bench.join(', ')}</strong>
      </div>

      {/* Gaps */}
      {combo.gaps?.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 11, color: 'var(--red)' }}>
          ⚠️ Gaps: {combo.gaps.slice(0, 4).join(' · ')}
          {combo.gaps.length > 4 && ` +${combo.gaps.length - 4} more`}
        </div>
      )}

      {/* Explanation */}
      {combo.explanation?.length > 0 && (
        <div style={{ marginTop: 10, padding: '8px 12px', background: 'var(--bg)', borderRadius: 8, fontSize: 12, color: 'var(--muted)' }}>
          {combo.explanation.map((e, i) => <div key={i}>• {e}</div>)}
        </div>
      )}
    </div>
  );
}

export default function LineupBuilder() {
  const [teamId, setTeamId] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!teamId) return;
    setLoading(true);
    getTeamLineup(teamId)
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [teamId]);

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Lineup Builder</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 24 }}>
        All 3-player combinations ranked by coverage breadth and combined strength.
      </p>

      <div style={{ marginBottom: 24 }}>
        <TeamSelector value={teamId} onChange={setTeamId} />
      </div>

      {loading && <div className="loading">Calculating lineups…</div>}

      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="card" style={{ background: 'var(--surface2)', display: 'flex', gap: 24 }}>
            <div>
              <span style={{ color: 'var(--muted)', fontSize: 12 }}>Roster size</span>
              <div style={{ fontWeight: 700, fontSize: 18 }}>{data.total_players} players</div>
            </div>
            <div>
              <span style={{ color: 'var(--muted)', fontSize: 12 }}>Combinations</span>
              <div style={{ fontWeight: 700, fontSize: 18 }}>{data.combinations?.length}</div>
            </div>
          </div>
          {(data.combinations || []).map((combo, i) => (
            <LineupCard key={i} combo={combo} isTop={combo.rank === 1} />
          ))}
        </div>
      )}

      {!teamId && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: 60, color: 'var(--muted)' }}>
          Select a team to generate lineup recommendations.
        </div>
      )}
    </div>
  );
}
