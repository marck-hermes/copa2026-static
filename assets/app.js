/**
 * Copa 2026 Static Site - Main App JS
 * Handles data rendering, timezone display, and staleness check.
 */

(function () {
  'use strict';

  const STALENESS_THRESHOLD_MS = 2 * 60 * 60 * 1000; // 2 hours

  function getTeamById(teams, id) {
    return teams.find(t => t.id === id) || { name: '?', flag_emoji: '', fifa_code: '?' };
  }

  function formatDate(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'America/Sao_Paulo'
    });
  }

  function formatDateShort(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'America/Sao_Paulo'
    });
  }

  function renderMatchCard(match, teams) {
    const teamA = getTeamById(teams, match.team_a_id);
    const teamB = getTeamById(teams, match.team_b_id);
    const scoreDisplay = (match.score_a !== null && match.score_b !== null)
      ? `${match.score_a}:${match.score_b}`
      : 'vs';
    const statusClass = match.status === 'final' ? 'status-final' : '';

    return `
      <div class="match-card ${statusClass}">
        <span class="match-date">${formatDateShort(match.date_utc)}</span>
        <div class="match-teams">
          <span class="match-team">
            <span class="emoji">${teamA.flag_emoji}</span>
            <span>${teamA.fifa_code}</span>
          </span>
          <span class="match-score">${scoreDisplay}</span>
          <span class="match-team">
            <span class="emoji">${teamB.flag_emoji}</span>
            <span>${teamB.fifa_code}</span>
          </span>
        </div>
        ${match.odds ? `<span class="match-odds">${match.odds}</span>` : ''}
      </div>
    `;
  }

  function updateStaleness() {
    const meta = window.META;
    if (!meta || !meta.build_time) return;

    const buildTime = new Date(meta.build_time).getTime();
    const now = Date.now();
    const ageMs = now - buildTime;
    const ageMin = Math.floor(ageMs / 60000);

    const el = document.getElementById('last-update');
    if (!el) return;

    if (ageMs > STALENESS_THRESHOLD_MS) {
      el.textContent = `⚠️ Dados desatualizados há ${ageMin} min`;
      el.classList.add('stale');
    } else {
      el.textContent = `Atualizado há ${ageMin} min`;
      el.classList.remove('stale');
    }
  }

  function init() {
    const data = window.APP_DATA;
    if (!data) return;

    updateStaleness();

    // Quick stats
    const quickStats = document.getElementById('quick-stats');
    if (quickStats && data.standings && data.matches) {
      const totalMatches = data.matches.length;
      const completed = data.matches.filter(m => m.status === 'final').length;
      const upcoming = data.matches.filter(m => m.status === 'scheduled').length;
      const totalGoals = data.standings.reduce((sum, s) => sum + s.gf, 0);

      quickStats.innerHTML = `
        <div class="stat-card">
          <div class="stat-value">${data.teams.length}</div>
          <div class="stat-label">Seleções</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${totalMatches}</div>
          <div class="stat-label">Jogos</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${completed}</div>
          <div class="stat-label">Finalizados</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${upcoming}</div>
          <div class="stat-label">Agendados</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${totalGoals}</div>
          <div class="stat-label">Gols</div>
        </div>
      `;
    }

    // Recent matches
    const recentEl = document.getElementById('recent-matches');
    if (recentEl && data.matches) {
      const recent = data.matches
        .filter(m => m.status === 'final')
        .sort((a, b) => new Date(b.date_utc) - new Date(a.date_utc))
        .slice(0, 10);
      recentEl.innerHTML = recent.map(m => renderMatchCard(m, data.teams)).join('');
    }

    // Upcoming matches
    const upcomingEl = document.getElementById('upcoming-matches');
    if (upcomingEl && data.matches) {
      const upcoming = data.matches
        .filter(m => m.status === 'scheduled')
        .sort((a, b) => new Date(a.date_utc) - new Date(b.date_utc))
        .slice(0, 10);
      upcomingEl.innerHTML = upcoming.map(m => renderMatchCard(m, data.teams)).join('');
    }
  }

  function initGroupsOverview() {
    const data = window.APP_DATA;
    if (!data || !data.standings) return;

    updateStaleness();

    const container = document.getElementById('groups-overview');
    if (!container) return;

    // Group standings by inferred groups (top 48 sorted by pts, groups of 4)
    const sorted = [...data.standings].sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);
    const groups = {};
    const groupLetters = 'ABCDEFGHIJKL';

    sorted.forEach((s, i) => {
      const letter = groupLetters[Math.floor(i / 4)];
      if (!groups[letter]) groups[letter] = [];
      groups[letter].push({ ...s, pos_in_group: (i % 4) + 1 });
    });

    container.innerHTML = groupLetters.split('').slice(0, 12).map(letter => {
      const teams = groups[letter] || [];
      return `
        <div class="group-card">
          <h3><a href="/grupos/grupo_${letter}.html">Grupo ${letter}</a></h3>
          ${teams.map((t, i) => {
            const team = getTeamById(data.teams, t.team_id);
            return `
              <div class="team-row">
                <span class="pos">${i + 1}</span>
                <span class="emoji">${team.flag_emoji}</span>
                <span class="team-name">${team.name}</span>
                <span class="pts">${t.pts}</span>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }).join('');
  }

  function initGroupDetail() {
    const data = window.APP_DATA;
    const letter = window.GROUP_LETTER;
    if (!data || !letter) return;

    updateStaleness();

    // Standings table
    const tableBody = document.querySelector('#standings-table tbody');
    if (tableBody && data.standings) {
      // Filter standings for this group (based on position in sorted list)
      const sorted = [...data.standings].sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);
      const groupLetters = 'ABCDEFGHIJKL';
      const groupIdx = groupLetters.indexOf(letter);
      const groupStandings = sorted.slice(groupIdx * 4, groupIdx * 4 + 4);

      tableBody.innerHTML = groupStandings.map((s, i) => {
        const team = getTeamById(data.teams, s.team_id);
        const isTop2 = i < 2;
        return `
          <tr class="${isTop2 ? 'top-2' : ''}">
            <td class="pos-${i + 1}">${i + 1}</td>
            <td>
              <div class="team-cell">
                <span class="emoji">${team.flag_emoji}</span>
                <span>${team.name}</span>
              </div>
            </td>
            <td>${s.mp}</td>
            <td>${s.w}</td>
            <td>${s.d}</td>
            <td>${s.l}</td>
            <td>${s.gf}</td>
            <td>${s.ga}</td>
            <td>${s.gd}</td>
            <td class="pts">${s.pts}</td>
          </tr>
        `;
      }).join('');
    }

    // Group matches
    const matchesEl = document.getElementById('group-matches');
    if (matchesEl && data.matches) {
      // Note: matches don't have group info in current data, show all for now
      const groupMatches = data.matches
        .filter(m => m.status === 'final')
        .sort((a, b) => new Date(b.date_utc) - new Date(a.date_utc))
        .slice(0, 6);

      if (groupMatches.length === 0) {
        matchesEl.innerHTML = '<p class="no-matches">Nenhum jogo finalizado neste grupo ainda.</p>';
      } else {
        matchesEl.innerHTML = groupMatches.map(m => renderMatchCard(m, data.teams)).join('');
      }
    }
  }

  function initScorers() {
    const data = window.APP_DATA;
    if (!data || !data.scorers) return;

    updateStaleness();

    const tableBody = document.querySelector('#scorers-table tbody');
    if (tableBody) {
      tableBody.innerHTML = data.scorers.map(s => {
        const team = getTeamById(data.teams, s.team_id);
        return `
          <tr>
            <td>${s.rank}</td>
            <td>${s.player}</td>
            <td>
              <span class="emoji">${team.flag_emoji}</span>
              ${team.fifa_code}
            </td>
            <td>${s.goals}</td>
            <td>${s.assists}</td>
            <td>${s.minutes_per_goal || '-'}</td>
          </tr>
        `;
      }).join('');
    }

    // Stats
    const statsEl = document.getElementById('scorers-stats');
    if (statsEl && data.scorers.length > 0) {
      const totalGoals = data.scorers.reduce((sum, s) => sum + s.goals, 0);
      const topScorer = data.scorers[0];
      statsEl.innerHTML = `
        <div class="stat-card">
          <div class="stat-value">${totalGoals}</div>
          <div class="stat-label">Gols dos Top 20</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${topScorer.goals}</div>
          <div class="stat-label">Gols do líder (${topScorer.player})</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${(totalGoals / data.scorers.length).toFixed(1)}</div>
          <div class="stat-label">Média de gols</div>
        </div>
      `;
    }
  }

  function initMatches() {
    const data = window.APP_DATA;
    if (!data || !data.matches) return;

    updateStaleness();

    function renderMatches(filter) {
      const list = document.getElementById('matches-list');
      if (!list) return;

      let matches = [...data.matches];

      if (filter.phase && filter.phase !== 'all') {
        matches = matches.filter(m => m.stage === filter.phase);
      }
      if (filter.status && filter.status !== 'all') {
        matches = matches.filter(m => m.status === filter.status);
      }

      matches.sort((a, b) => new Date(a.date_utc) - new Date(b.date_utc));

      if (matches.length === 0) {
        list.innerHTML = '<p>Nenhum jogo encontrado com esses filtros.</p>';
        return;
      }

      list.innerHTML = matches.map(m => renderMatchCard(m, data.teams)).join('');
    }

    const phaseFilter = document.getElementById('phase-filter');
    const statusFilter = document.getElementById('status-filter');

    function applyFilters() {
      renderMatches({
        phase: phaseFilter?.value || 'all',
        status: statusFilter?.value || 'all'
      });
    }

    if (phaseFilter) phaseFilter.addEventListener('change', applyFilters);
    if (statusFilter) statusFilter.addEventListener('change', applyFilters);

    renderMatches({ phase: 'all', status: 'all' });
  }

  // Expose globally
  window.App = {
    init,
    initGroupsOverview,
    initGroupDetail,
    initScorers,
    initMatches
  };
})();