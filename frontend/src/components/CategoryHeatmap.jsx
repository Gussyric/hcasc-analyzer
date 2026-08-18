// CategoryHeatmap: color-coded grid of category accuracies
// accuracy 0-40% = red, 40-65% = yellow, 65%+ = green

function getColor(accuracy) {
  if (accuracy >= 0.65) return { bg: 'var(--green-soft)', text: 'var(--green)' };
  if (accuracy >= 0.40) return { bg: 'var(--yellow-soft)', text: 'var(--yellow)' };
  return { bg: 'var(--red-soft)', text: 'var(--red)' };
}

export default function CategoryHeatmap({ coverage }) {
  if (!coverage || Object.keys(coverage).length === 0) {
    return <div className="loading">No category data available.</div>;
  }

  const entries = Object.entries(coverage).sort((a, b) => b[1].best_accuracy - a[1].best_accuracy);

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
      gap: 8,
    }}>
      {entries.map(([cat, data]) => {
        const { bg, text } = getColor(data.best_accuracy);
        return (
          <div key={cat} style={{
            background: bg,
            border: `1px solid ${text}33`,
            borderRadius: 8,
            padding: '10px 12px',
          }}>
            <div style={{ fontSize: 11, color: text, fontWeight: 700, marginBottom: 4 }}>
              {(data.best_accuracy * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: 12, color: 'var(--text)', fontWeight: 500, lineHeight: 1.3 }}>
              {cat}
            </div>
            {data.best_player && (
              <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                ↑ {data.best_player}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
