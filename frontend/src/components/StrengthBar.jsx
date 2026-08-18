export default function StrengthBar({ value, showLabel = true }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 65 ? 'var(--green)' : pct >= 40 ? 'var(--yellow)' : 'var(--red)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div className="strength-bar-wrap" style={{ flex: 1 }}>
        <div className="strength-bar" style={{ width: `${pct}%`, background: color }} />
      </div>
      {showLabel && (
        <span style={{ fontSize: 13, fontWeight: 700, color, minWidth: 38, textAlign: 'right' }}>
          {pct}%
        </span>
      )}
    </div>
  );
}
