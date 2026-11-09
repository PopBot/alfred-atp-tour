# Use Hybrid ESPN + Official ATP Tour JSON APIs

Status: accepted

We will combine ESPN's public tennis JSON API (`site.api.espn.com`, `sports.core.api.espn.com`, `site.web.api.espn.com`) with the official, keyless ATP Tour JSON endpoints (`www.atptour.com/en/-/...` and `app.atptour.com/api/v2/gateway/livematches`) rather than relying on a single upstream provider.

## Context & Trade-offs

- **ESPN Public API**: Provides fast (~120ms), unified tournament scoreboards (`/sports/tennis/atp/scoreboard`), Top 150 Singles rankings (`/sports/tennis/atp/rankings`), high-resolution player headshots (`a.espncdn.com/i/headshots/tennis/players/full/{id}.png`), and country flags (`a.espncdn.com/i/teamlogos/countries/500/{ioc}.png`). However, ESPN's `/athletes/{id}/overview` returns empty `"statistics": {}` for tennis, its Core API only returns career totals (no current-season W-L or Service/Return stats), its scoreboard lacks live in-game point scores (`40-15`) and server indicators, and fetching a full-year calendar via `?dates=2026` downloads a 20.5 MB payload.
- **Official ATP Tour JSON Endpoints**: Provide a lightweight (~80 KB) full-season tournament calendar (`/en/-/tournaments/calendar/tour`) with surface, indoor/outdoor, tier badges, and prize money; rich current-season player service and return statistics (`/en/-/www/stats/{code}/{year}/all` and `/en/-/www/players/hero/{code}`); and live point-by-point scores (`app.atptour.com/api/v2/gateway/livematches/website`). However, ATP's official rankings page is HTML-only (no clean JSON API).
- **SofaScore (`api.sofascore.com`)**: Blocked by Cloudflare 403 bot protection when accessed from Python clients.

## Consequences

- Scoreboard (`atp`), Rankings (`atpr`), and Tournament Draw (`atpt`) views stay fast and consistent using ESPN's CDN (with optional live point/server enrichment from the ATP live gateway when matches are actively in progress).
- Schedule (`atps`) uses the official ATP Tour calendar JSON (`atptour.com/en/-/tournaments/calendar/tour`).
- Player Search & Stats (`atpp`) bridges ESPN athlete search/headshots/career stats with `atptour.com` player search (`/en/-/ajax/playersearch/PlayerUrlSearch`) to populate 2026 YTD W-L, Titles, Prize Money, `⌘` Service Stats, and `⌥` Return Stats.
