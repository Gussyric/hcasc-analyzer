import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export const getTeams = (tournamentId = null) =>
  api.get(`/teams/${tournamentId ? `?tournament_id=${tournamentId}` : ''}`);
export const getTeamOverview = (id, tournamentId = null) =>
  api.get(`/teams/${id}/overview${tournamentId ? `?tournament_id=${tournamentId}` : ''}`);
export const getTeamPlayers = (id) => api.get(`/teams/${id}/players`);
export const getTeamLineup = (id) => api.get(`/teams/${id}/lineup`);
export const getTeamUC = (id, opponentId = null) =>
  api.get(`/teams/${id}/ultimate-challenge${opponentId ? `?opponent_id=${opponentId}` : ''}`);
export const getMatchup = (team1, team2) => api.get(`/matchup/?team1=${team1}&team2=${team2}`);
export const getTournaments = () => api.get('/tournaments/');
export const uploadPDF = (file, tournamentId = null) => {
  const form = new FormData();
  form.append('file', file);
  if (tournamentId) form.append('tournament_id', tournamentId);
  return api.post('/upload/pdf', form);
};

export default api;
