/**
 * Copa 2026 Static Site - Bracket Renderer
 * Rounds knockout bracket matches into visual layout.
 */

(function () {
  'use strict';

  function getTeamById(teams, id) {
    return teams.find(t => t.id === id) || { name: '?', flag_emoji: '', fifa_code: '?' };
  }

  function renderBracketRound(teams, matches, round) {
    const roundMatches = matches.filter(m => m.round === round);
    if (roundMatches.length === 0) return '';

    return roundMatches.map(m => {
      const teamA = m.team_a_id ? getTeamById(teams, m.team_a_id) : null;
      const teamB = m.team_b_id ? getTeamById(teams, m.team_b_id) : null;
      const scoreA = m.score_a !== null ? m.score_a : '';
      const scoreB = m.score_b !== null ? m.score_b : '';

      return `
        <div class="bracket-bracket-item ${m.status === 'final' ? 'has-winner' : ''}">
          <div class="bracket-team">
            <span class="emoji">${teamA ? teamA.flag_emoji : '❓'}</span>
            <span class="${m.status === 'final' && m.score_a > m.score_b ? 'match-winner-name' : ''}">
              ${teamA ? teamA.fifa_code : 'TBD'}
            </span>
            <span class="bracket-score">${scoreA}</span>
          </div>
          <div class="bracket-team">
            <span class="emoji">${teamB ? teamB.flag_emoji : '❓'}</span>
            <span class="${m.status === 'final' && m.score_b > m.score_a ? 'match-winner-name' : ''}">
              ${teamB ? teamB.fifa_code : 'TBD'}
            </span>
            <span class="bracket-score">${scoreB}</span>
          </div>
          <div class="bracket-bracket-status">${m.status === 'final' ? 'Final' : 'Agendado'}</div>
        </div>
      `;
    }).join('');
  }

  function init() {
    const data = window.APP_DATA;
    if (!data || !data.bracket || !data.teams) return;

    const rounds = ['32', '16', '8', '4', '3rd'];
    rounds.forEach(round => {
      const container = document.querySelector(`[data-round="${round}"]`);
      if (container) {
        container.innerHTML = renderBracketRound(data.teams, data.bracket, round);
      }
    });

    // Filter handler
    const filter = document.getElementById('round-filter');
    if (filter) {
      filter.addEventListener('change', function () {
        const sections = document.querySelectorAll('.bracket-container');
        sections.forEach(s => {
          s.style.display = (this.value === 'all' || s.id === `bracket-${this.value}`) ? '' : 'none';
        });
      });
    }
  }

  window.BracketRenderer = { init };
})();