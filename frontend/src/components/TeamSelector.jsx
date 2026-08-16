import { useEffect, useState } from 'react';
import { getTeams } from '../api';

export default function TeamSelector({ value, onChange, label = 'Select team', tournamentId = null }) {
  const [teams, setTeams] = useState([]);

  useEffect(() => {
    getTeams(tournamentId).then(r => {
      setTeams(r.data);
      // If a tournament filter narrows the list and the current selection
      // isn't in it anymore, clear it rather than leave a stale/invisible
      // selection pointing at a team not shown in the dropdown.
      if (value && !r.data.some(t => t.id === value)) {
        onChange(null);
      }
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tournamentId]);

  return (
    <select value={value || ''} onChange={e => onChange(Number(e.target.value))}>
      <option value="">{label}</option>
      {teams.map(t => (
        <option key={t.id} value={t.id}>
          {t.name} ({(t.overall_strength * 100).toFixed(0)}%) {t.wins}W-{t.losses}L
        </option>
      ))}
    </select>
  );
}
