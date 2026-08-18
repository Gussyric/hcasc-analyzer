import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import TeamOverview from './pages/TeamOverview';
import PlayerProfiles from './pages/PlayerProfiles';
import LineupBuilder from './pages/LineupBuilder';
import UltimateChallenge from './pages/UltimateChallenge';
import HeadToHead from './pages/HeadToHead';
import About from './pages/About';
import './index.css';

const NAV = [
  { to: '/',                  label: '📊 Team Overview' },
  { to: '/players',           label: '👤 Players' },
  { to: '/lineup',            label: '⚡ Lineup Builder' },
  { to: '/ultimate-challenge',label: '🏆 Ultimate Challenge' },
  { to: '/head-to-head',      label: '⚔️  Head-to-Head' },
  { to: '/about',             label: 'ℹ️  About' },
];

function getInitialTheme() {
  const saved = localStorage.getItem('theme');
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export default function App() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        {/* Sidebar */}
        <aside style={{
          width: 220, background: 'var(--surface)', borderRight: '1px solid var(--border)',
          padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: 8,
          position: 'sticky', top: 0, height: '100vh',
        }}>
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', letterSpacing: 1 }}>
              HCASC ANALYZER
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
              Team & Player Intelligence
            </div>
          </div>

          {NAV.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              style={({ isActive }) => ({
                display: 'block',
                padding: '9px 14px',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 500,
                color: isActive ? 'var(--on-accent)' : 'var(--muted)',
                background: isActive ? 'var(--accent)' : 'transparent',
                transition: 'all 0.15s',
              })}
            >
              {label}
            </NavLink>
          ))}

          <div style={{ flex: 1 }} />

          <button
            className="theme-toggle"
            onClick={() => setTheme(t => (t === 'dark' ? 'light' : 'dark'))}
          >
            {theme === 'dark' ? '☀️ Light mode' : '🌙 Dark mode'}
          </button>
        </aside>

        {/* Main content */}
        <main style={{ flex: 1, padding: '32px 36px', overflowY: 'auto' }}>
          <Routes>
            <Route path="/"                   element={<TeamOverview />} />
            <Route path="/players"            element={<PlayerProfiles />} />
            <Route path="/lineup"             element={<LineupBuilder />} />
            <Route path="/ultimate-challenge" element={<UltimateChallenge />} />
            <Route path="/head-to-head"       element={<HeadToHead />} />
            <Route path="/about"              element={<About />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
