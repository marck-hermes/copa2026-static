# DISCOVERY: Copa 2026 Static Site

## Data Source: native-stats.org/competition/WC/
- **Format:** HTML page with embedded data (standings, matches, scorers)
- **Content:**
  - 48 teams, 12 groups (A-L)
  - Standings: pos, team, MP, pts, GD, goals, form
  - Recent matches: date, match, score, odds
  - Upcoming matches: date/time (UTC), match, odds
  - Top scorers: player, team, goals, assists
- **Update frequency:** Appears to update in near real-time (matches from June 26-27, 2026 shown)
- **No API** — must parse HTML
- **CORS:** Likely blocks browser fetch → need server-side/build-time fetch

## Visual Reference: Excel Easy Tabela Copa 2026
- **Structure:** 3 tabs → Repescagem, Grupos (12 groups A-L), Mata-Mata (32, oitavas, quartas, semi, final, 3º lugar)
- **Key visual:** Bracket/eliminatória tree with team names, scores, progression lines
- **Grupo view:** Table with team, games, W/D/L, GF/GA/GD, pts
- **Mata-Mata view:** Classic tournament bracket

## Requirements from User
- Static site (HTML/CSS/JS)
- Auto-update every 15 minutes
- Deploy to Vercel (existing workflow)
- Match the bracket visual style

## Technical Constraints
- No backend — static files only
- Fetch must happen at build time (GitHub Action / Vercel Cron)
- Parser must be defensive (HTML structure may change)
- Timezone: source uses UTC, display in user local time ( 브라질 = UTC-3)
- 48 teams → 12 groups → 32 knockout → bracket

## Open Questions
1. Does native-stats.org have knockout stage data (bracket pairings) or only group stage?
2. How to determine knockout bracket pairings (1A vs 2B, etc.) — FIFA rules or simulate?
3. Should we show group standings tables + bracket, or just bracket?
4. Vercel Cron (free tier = 1/day) vs GitHub Actions (can run every 15 min)?
5. Host images (flags) locally or use emoji flags?

## Next Steps
→ Generate SPEC.md using project-planning skill template