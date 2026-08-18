import { useState, useEffect } from 'react';
import { getTeamPlayers } from '../api';
import TeamSelector from '../components/TeamSelector';
import StrengthBar from '../components/StrengthBar';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

function getBarColor(val) {
  if (val >= 65) return 'var(--green)';
  if (val >= 40) return 'var(--yellow)';
  return 'var(--red)';
}

function PlayerCard({ player, isSelected, onClick }) {
  return (
    <div
      className="card"
      onClick={onClick}
      style={{
        cursor: 'pointer',
        border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
        background: isSelected ? 'var(--accent-soft)' : 'var(--surface)',
        transition: 'all 0.15s',
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: 6 }}>{player.name}</div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>
        {player.category_stats?.length || 0} categories played
      </div>
      <StrengthBar value={player.overall_strength} />
    </div>
  );
}

export default function PlayerProfiles() {
  const [teamId, setTeamId] = useState(null);
  const [players, setPlayers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!teamId) return;
    setLoading(true);
    setSelected(null);
    getTeamPlayers(teamId)
      .then(r => { setPlayers(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [teamId]);

  const player = selected !== null ? players[selected] : null;
  const chartData = player
    ? (player.category_stats || [])
        .sort((a, b) => b.accuracy - a.accuracy)
        .map(s => ({ cat: s.category.length > 16 ? s.category.slice(0, 14) + '…' : s.category, acc: Math.round(s.accuracy * 100), buzzed: s.buzzed_in, correct: s.answered_correctly }))
    : [];

  const games = player?.points_per_game || [];
  const gameAverages = games.length > 0 ? {
    player_points: games.reduce((sum, g) => sum + g.player_points, 0) / games.length,
    team_game_points: games.reduce((sum, g) => sum + g.team_game_points, 0) / games.length,
    share_of_game: games.reduce((sum, g) => sum + g.share_of_game, 0) / games.length,
  } : null;

  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Player Profiles</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 24 }}>
        Individual player performance broken down by category.
      </p>

      <div style={{ marginBottom: 24 }}>
        <TeamSelector value={teamId} onChange={setTeamId} />
      </div>

      {loading && <div className="loading">Loading…</div>}

      {players.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 20 }}>
          {/* Player list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {players.map((p, i) => (
              <PlayerCard
                key={p.id}
                player={p}
                isSelected={selected === i}
                onClick={() => setSelected(i)}
              />
            ))}
          </div>

          {/* Detail panel */}
          {player ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Header */}
              <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 20, fontWeight: 800 }}>{player.name}</div>
                  <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 2 }}>{player.team_name}</div>
                </div>
                <div style={{ display: 'flex', gap: 24 }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--accent)' }}>
                      {(player.overall_strength * 100).toFixed(1)}%
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>overall strength</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--green)' }}>
                      {player.season_player_points}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      pts earned ({(player.season_points_share * 100).toFixed(1)}% of team's {player.team_season_total_points})
                    </div>
                  </div>
                </div>
              </div>

              {/* Accuracy by category bar chart */}
              <div className="card">
                <div style={{ fontWeight: 700, marginBottom: 16 }}>Accuracy by Category</div>
                <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 28)}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
                    <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 11 }} tickFormatter={v => `${v}%`} />
                    <YAxis type="category" dataKey="cat" tick={{ fill: 'var(--text)', fontSize: 11 }} width={140} />
                    <Tooltip
                      contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 12 }}
                      formatter={(v) => [`${v}%`, 'Accuracy']}
                    />
                    <Bar dataKey="acc" radius={[0, 4, 4, 0]}>
                      {chartData.map((entry, i) => (
                        <Cell key={i} fill={getBarColor(entry.acc)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Stats table */}
              <div className="card">
                <div style={{ fontWeight: 700, marginBottom: 12 }}>Detailed Stats</div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: 'var(--muted)', textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                      <th style={{ padding: '6px 8px' }}>Category</th>
                      <th style={{ padding: '6px 8px', textAlign: 'right' }}>Heard</th>
                      <th style={{ padding: '6px 8px', textAlign: 'right' }}>Buzzed</th>
                      <th style={{ padding: '6px 8px', textAlign: 'right' }}>Correct</th>
                      <th style={{ padding: '6px 8px', textAlign: 'right' }}>Accuracy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(player.category_stats || [])
                      .sort((a, b) => b.accuracy - a.accuracy)
                      .map(s => {
                        const color = s.accuracy >= 0.65 ? 'var(--green)' : s.accuracy >= 0.40 ? 'var(--yellow)' : 'var(--red)';
                        return (
                          <tr key={s.category} style={{ borderBottom: '1px solid var(--border)' }}>
                            <td style={{ padding: '8px 8px' }}>{s.category}</td>
                            <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--muted)' }}>{s.questions_heard}</td>
                            <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--muted)' }}>{s.buzzed_in}</td>
                            <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--muted)' }}>{s.answered_correctly}</td>
                            <td style={{ padding: '8px 8px', textAlign: 'right', fontWeight: 700, color }}>{(s.accuracy * 100).toFixed(0)}%</td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>

              {/* Points by game */}
              {player.points_per_game?.length > 0 && (
                <div className="card">
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>Points by Game</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>
                    Face-Off + Bonus points only — Ultimate Challenge points aren't attributed to a single player.
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ color: 'var(--muted)', textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                        <th style={{ padding: '6px 8px' }}>Game</th>
                        <th style={{ padding: '6px 8px' }}>Opponent</th>
                        <th style={{ padding: '6px 8px', textAlign: 'right' }}>Player Pts</th>
                        <th style={{ padding: '6px 8px', textAlign: 'right' }}>Team Total</th>
                        <th style={{ padding: '6px 8px', textAlign: 'right' }}>Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      {player.points_per_game.map((g, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '8px 8px', color: 'var(--muted)' }}>Rm{g.room} Gm{g.game}</td>
                          <td style={{ padding: '8px 8px' }}>{g.opponent}</td>
                          <td style={{ padding: '8px 8px', textAlign: 'right', fontWeight: 700 }}>{g.player_points}</td>
                          <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--muted)' }}>{g.team_game_points}</td>
                          <td style={{ padding: '8px 8px', textAlign: 'right', fontWeight: 700, color: 'var(--accent)' }}>
                            {(g.share_of_game * 100).toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    {gameAverages && (
                      <tfoot>
                        <tr style={{ borderTop: '2px solid var(--border)' }}>
                          <td style={{ padding: '8px 8px', fontWeight: 700 }} colSpan={2}>Average ({games.length} games)</td>
                          <td style={{ padding: '8px 8px', textAlign: 'right', fontWeight: 700 }}>{gameAverages.player_points.toFixed(1)}</td>
                          <td style={{ padding: '8px 8px', textAlign: 'right', color: 'var(--muted)', fontWeight: 700 }}>{gameAverages.team_game_points.toFixed(1)}</td>
                          <td style={{ padding: '8px 8px', textAlign: 'right', fontWeight: 700, color: 'var(--accent)' }}>
                            {(gameAverages.share_of_game * 100).toFixed(1)}%
                          </td>
                        </tr>
                      </tfoot>
                    )}
                  </table>
                </div>
              )}
            </div>
          ) : (
            <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)' }}>
              Select a player to view their profile.
            </div>
          )}
        </div>
      )}

      {!teamId && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: 60, color: 'var(--muted)' }}>
          Select a team to view player profiles.
        </div>
      )}
    </div>
  );
}
