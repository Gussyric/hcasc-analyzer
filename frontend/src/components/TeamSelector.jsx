import { useEffect, useState } from 'react';
import { getTeams } from '../api';

export default function TeamSelector({ value, onChange, label = 'Select team' }) {
  const [teams, setTeams] = useState([]);

  useEffect(() => {
    getTeams().then(r => setTeams(r.data)).catch(() => {});
  }, []);

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
