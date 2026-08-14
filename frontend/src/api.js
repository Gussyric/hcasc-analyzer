import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export const getTeams = () => api.get('/teams/');
export const getTeamOverview = (id) => api.get(`/teams/${id}/overview`);
export const getTeamPlayers = (id) => api.get(`/teams/${id}/players`);
export const getTeamLineup = (id) => api.get(`/teams/${id}/lineup`);
export const getTeamUC = (id, opponentId = null) =>
  api.get(`/teams/${id}/ultimate-challenge${opponentId ? `?opponent_id=${opponentId}` : ''}`);
export const getMatchup = (team1, team2) => api.get(`/matchup/?team1=${team1}&team2=${team2}`);
export const uploadPDF = (file) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/upload/pdf', form);
};

export default api;
