import { useState, useEffect } from 'react';
import { getTournaments, getTeams } from '../api';

const PAGES = [
  {
    icon: '📊',
    name: 'Team Overview',
    desc: 'A team\'s overall strength, win/loss record (round-robin + playoffs), category coverage heatmap, and roster strength. Can be scoped to a single tournament instead of the team\'s all-time aggregate.',
  },
  {
    icon: '👤',
    name: 'Players',
    desc: 'Per-player accuracy broken down by category, plus a points-earned breakdown per game and their share of the team\'s total score.',
  },
  {
    icon: '⚡',
    name: 'Lineup Builder',
    desc: 'Every 3-of-4 player combination for a team, ranked by category coverage and combined strength, with an explanation of what\'s lost by benching each player.',
  },
  {
    icon: '🏆',
    name: 'Ultimate Challenge',
    desc: 'A team\'s UC category history, a recommended category to pick next (optionally weighed against a specific opponent\'s known weaknesses), and full category-by-category stats.',
  },
  {
    icon: '⚔️',
    name: 'Head-to-Head',
    desc: 'Compares two teams directly — category-by-category advantages, player-vs-player matchups by strength rank, UC strategy, and a scouting report.',
  },
];

function Card({ children, style }) {
  return <div className="card" style={style}>{children}</div>;
}

function SectionTitle({ children }) {
  return <h2 style={{ fontSize: 18, fontWeight: 700, margin: '28px 0 12px' }}>{children}</h2>;
}

export default function About() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    Promise.all([getTournaments(), getTeams()])
      .then(([t, teams]) => setStats({ tournaments: t.data.length, teams: teams.data.length }))
      .catch(() => {});
  }, []);

  return (
    <div>
      <h1 style={{ fontSize: 26, fontWeight: 800, marginBottom: 4 }}>About HCASC Analyzer</h1>
      <p style={{ color: 'var(--muted)', marginBottom: 24 }}>
        What this tool is, how the data gets here, and how the numbers are calculated.
      </p>

      <Card style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
        <p style={{ lineHeight: 1.7, flex: '2 1 420px', maxWidth: 640 }}>
          HCASC Analyzer turns official HCASC National Qualifying Tournament (NQT) scoresheets and
          results PDFs into team and player intelligence — category strengths and gaps, lineup
          recommendations, Ultimate Challenge strategy, and head-to-head scouting reports.
        </p>
        {stats && (
          <div style={{ display: 'flex', gap: 36, flex: '1 1 200px' }}>
            <div>
              <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--accent)' }}>{stats.tournaments}</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>tournaments tracked</div>
            </div>
            <div>
              <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--gold)' }}>{stats.teams}</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>teams</div>
            </div>
          </div>
        )}
      </Card>

      <SectionTitle>What each page does</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16 }}>
        {PAGES.map(p => (
          <Card key={p.name} style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
            <div style={{ fontSize: 22 }}>{p.icon}</div>
            <div>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>{p.name}</div>
              <div style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>{p.desc}</div>
            </div>
          </Card>
        ))}
      </div>

      <SectionTitle>How "Overall Strength" is calculated</SectionTitle>
      <Card>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) minmax(280px, 1.4fr)', gap: 28 }}>
          <div>
            <p style={{ fontSize: 13, lineHeight: 1.7 }}>
              One weighted average, combining every category a team has faced with their Ultimate
              Challenge performance:
            </p>
            <div style={{
              background: 'var(--surface2)', borderRadius: 8, padding: '14px 16px', margin: '14px 0 0',
              fontSize: 13, fontFamily: 'monospace', color: 'var(--accent)', lineHeight: 1.8,
            }}>
              strength = Σ(category_accuracy × attempts) + (UC_accuracy × UC_attempts)
              <br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;÷ Σ(attempts) + UC_attempts
            </div>
            <p style={{ marginTop: 14, fontSize: 13, color: 'var(--muted)', lineHeight: 1.7 }}>
              Category <em>coverage</em> (the heatmap, "top/weak categories") is different — that
              uses each category's <em>best</em> player, since "does someone on this roster know
              this" is a best-player question even though overall strength isn't.
            </p>
          </div>
          <ul style={{ paddingLeft: 20, fontSize: 13, color: 'var(--muted)', lineHeight: 1.9, margin: 0 }}>
            <li style={{ marginBottom: 12 }}><strong style={{ color: 'var(--text)' }}>Category accuracy is pooled across the whole roster</strong> — total correct ÷ total attempts for everyone who's faced that category, not just whoever did best. Players are assigned by round in this format, not routed to their specialty, so a team-wide number is more realistic than a single star's ceiling.</li>
            <li style={{ marginBottom: 12 }}><strong style={{ color: 'var(--text)' }}>Every term is weighted by its own sample size.</strong> A category decided over 10 questions counts far more than one decided by a single buzz — and a 0% result counts too, since silently dropping bad categories would be its own kind of bias.</li>
            <li><strong style={{ color: 'var(--text)' }}>UC is folded in as one more weighted term</strong>, not a separate fixed percentage — it's worth up to 500 points a game, often more than the entire Face-Off round, so it earns influence proportional to how much of it a team has actually played.</li>
          </ul>
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 16, marginTop: 28 }}>
        <div>
          <SectionTitle>Where the data comes from</SectionTitle>
          <Card>
            <p style={{ lineHeight: 1.7, fontSize: 13 }}>
              Two kinds of official PDFs feed the app, uploaded per-tournament from the
              "+ Upload PDF" control on Team Overview:
            </p>
            <ul style={{ marginTop: 10, paddingLeft: 20, fontSize: 13, color: 'var(--muted)', lineHeight: 1.9 }}>
              <li><strong style={{ color: 'var(--text)' }}>Scoresheets</strong> — one per game, giving every Face-Off question's category and points, plus the Ultimate Challenge result</li>
              <li><strong style={{ color: 'var(--text)' }}>Summary documents</strong> — PlayerStats, ResultsByTeam, RoundRobinResults, and PlayoffResults, giving official per-category player accuracy and standings</li>
            </ul>
            <p style={{ marginTop: 10, fontSize: 13, color: 'var(--muted)', lineHeight: 1.7 }}>
              Re-uploading a file that's already been processed is a safe no-op — every import is
              checked against a hash of the file's contents before anything is written.
            </p>
          </Card>
        </div>

        <div>
          <SectionTitle>Good to know</SectionTitle>
          <Card>
            <ul style={{ paddingLeft: 20, fontSize: 13, color: 'var(--muted)', lineHeight: 1.9, margin: 0 }}>
              <li style={{ marginBottom: 10 }}>Ultimate Challenge points aren't attributed to a specific player — it's a whole-team category pick, so player point totals only ever cover Face-Off + Bonus.</li>
              <li style={{ marginBottom: 10 }}>"Record" and "Points Scored" combine round-robin and playoff games; the breakdown between the two is shown in the small text underneath.</li>
              <li>A handful of Face-Off rows (well under 1% of all questions) get skipped rather than recorded when a category name is a bare number with no letters at all to anchor the parser on — safer to drop than to risk a corrupted category or player name.</li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
