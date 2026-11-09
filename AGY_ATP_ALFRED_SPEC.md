# 🎯 ATP Tour (`atp`) Alfred Workflow — Specification & Architecture Plan

## 1. Overview
Build a standalone, zero-dependency Alfred 5 workflow for the **Men's ATP Tour** (`atp`) inside `/Users/jarodwong/Documents/Alfred Workflows/atp/alfred-atp-tour/`. It evolves the architecture of [alfred-mlb-scores](file:///Users/jarodwong/Documents/Alfred%20Workflows/mlb/alfred-mlb-scores), [alfred-nfl-scores](file:///Users/jarodwong/Documents/Alfred%20Workflows/nfl/alfred-nfl-scores), and [alfred-ncaaf-scores](file:///Users/jarodwong/Documents/Alfred%20Workflows/ncaaf/alfred-ncaaf-scores), adapted for men's professional tournament tennis.

### Key Architectural Highlights
- **Hybrid Zero-Auth API Architecture ([ADR-0001](file:///Users/jarodwong/Documents/Alfred%20Workflows/atp/docs/adr/0001-hybrid-espn-and-official-atp-api-architecture.md))**:
  - **ESPN Public Tennis API** (`site.api.espn.com`, `sports.core.api.espn.com`, `site.web.api.espn.com`) powers the Tournament & Match Scoreboard, Top 150 Singles Rankings, Player Headshots, Country Flag PNGs, and parallelized Player Match Eventlogs.
  - **Official ATP Tour JSON Endpoints** (`www.atptour.com/en/-/...` & `app.atptour.com/api/v2/gateway/livematches`) power the Full-Season Tournament Calendar, live point-by-point game score & server enrichment, 2026 YTD W-L/Titles/Prize Money, and 2026 Service (`⌘`) & Return (`⌥`) statistics.
- **Official ATP Tour Workflow Logo (`icon.png`)**: Rendered from the official ATP Tour vector mark (`File:ATP Tour logo.svg` via Wikimedia Commons) centered onto a crisp 64×64 square PNG.
- **Boundary-Aware Subcommand Routing ([ADR-0002](file:///Users/jarodwong/Documents/Alfred%20Workflows/atp/docs/adr/0002-boundary-aware-subcommand-routing.md))**: Single Script Filter (`keyword: atp`, `withspace: false`) distinguishes space-separated scoreboard filters (`atp sinner`, `atp paris`, `atp doubles`, `atp live`) from attached subcommand suffixes (`atpr`, `atps`, `atpt`, `atpp`).
- **Dual Country Flag Matchup Icons + Player Headshots**:
  - **Scoreboard (`atp`) & Tournament Draw (`atpt`)**: Composite 64×64 side-by-side Country Flag icons (`matchup_{ioc1}_{ioc2}.png`) via [`image_utils.py`](file:///Users/jarodwong/Documents/Alfred%20Workflows/ncaaf/alfred-ncaaf-scores/image_utils.py) so 30+ matches across main and qualifying draws render in <50ms without missing-image gaps, paired with inline flag emojis (`🇪🇸`, `🇮🇹`, `🇺🇸`).
  - **Rankings (`atpr`) & Player Search (`atpp`)**: High-resolution ESPN Player Headshots (`headshots/{athlete_id}.png`, 7-day cache TTL) with Country Flag PNG fallback.
- **URL Sanitization**: Strips broken `https://www.espn.com/null/player/...` links returned by ESPN's rankings endpoint and normalizes them to valid `https://www.espn.com/tennis/player/_/id/{id}/{slug}` and `https://www.atptour.com/en/players/{slug}/{code}/overview` URLs.

---

## 2. Alfred Keystroke Commands & UX Flow

A single Script Filter in `info.plist` (`keyword: atp`, `withspace: false`) passes `"$1"` (unstripped) to `python3 atp.py "$1"`:

| Command | Raw `$1` | Routed Module & Behavior |
| :--- | :--- | :--- |
| `atp` | `""` | **Scoreboard (`atp.py`)**: Smart Active Window of current ATP tournaments—`Live` matches first, then `Today` Upcoming/Final matches, then recent Main Draw matches (`Singles` default). |
| `atp {filter}` | `" {filter}"` (starts with space) | **Filtered Scoreboard (`atp.py`)**: Filters active tournament matches by player (`atp alcaraz`), tournament (`atp paris`), `atp live`, `atp doubles`, `atp qual`, or `atp all`. |
| `atpr` / `atpr {query}` | `"r"` or `"r {query}"` | **Rankings (`atp_rankings.py`)**: Official PIF ATP Singles Rankings (Top 50 default; supports `atpr top10`, `atpr top25`, `atpr all` for Top 150, player name `atpr sinner`, or country `atpr usa`, `atpr ita`). |
| `atps` / `atps {query}` | `"s"` or `"s {query}"` | **Tour Schedule / Calendar (`atp_schedule.py`)**: Full-season ATP Tour & Grand Slam calendar grouped by `Active This Week` → `Upcoming` → `Completed`. Filter by tier (`atps slam`, `atps 1000`, `atps 500`, `atps 250`), surface (`atps clay`, `atps grass`, `atps hard`, `atps indoor`), month (`atps may`), or city/name. |
| `atpt` / `atpt {query}` | `"t"` or `"t {query}"` | **Tournament Draw & Results (`atp_tournament.py`)**: Full round-by-round Main Draw progression (`Final` → `Semifinals` → `Quarterfinals` → `R16` → `R32` → `R64` → `R128`) for active tournaments. Supports `atpt doubles` or tournament name filter. |
| `atpp {player}` | `"p {player}"` | **Unified Player Profile, Stats & Recent Matches (`atp_player.py`)**: Multi-match shows matching ATP players with rank, YTD & Career W-L/Titles/Prize, `⌘` Serve stats, and `⌥` Return stats. Single-player match shows Row 1 as Player Overview + Rows 2–11 as the player's last 10 tournament matches inline. |

---

## 3. Directory & File Structure

```text
atp/
├── CONTEXT.md                  ← Domain model & ubiquitous language glossary
├── AGY_ATP_ALFRED_SPEC.md      ← This specification and architecture plan
├── docs/
│   └── adr/
│       ├── 0001-hybrid-espn-and-official-atp-api-architecture.md
│       └── 0002-boundary-aware-subcommand-routing.md
└── alfred-atp-tour/            ← Workflow source & packaging root (when implemented)
    ├── atp.py                  ← Router + Smart Active Window Match Scoreboard
    ├── atp_rankings.py         ← Top 150 ATP Singles Rankings (with Country / Slice / Player filters)
    ├── atp_schedule.py         ← Full-Season ATP Tournament Calendar (Active / Upcoming / Completed)
    ├── atp_tournament.py       ← Round-by-round Tournament Draw & Results viewer
    ├── atp_player.py           ← Unified Player Profile (⌘ Serve / ⌥ Return) + Inline Recent Matches
    ├── utils.py                ← Cache, HTTP session, IOC flag emoji & PNG helpers, set linescore formatter
    ├── image_utils.py          ← Pure-Python PNG decoder, resizer, and dual-flag matchup compositor
    ├── download_assets.py      ← One-time build script for official ATP `icon.png` and common IOC flags
    ├── build.py                ← Packages `ATP Tour.alfredworkflow`
    ├── info.plist              ← Alfred 5 workflow XML (`keyword: atp`, `withspace: false`)
    ├── icon.png                ← Official ATP Tour 64×64 PNG workflow icon
    ├── flags/                  ← Pre-bundled 64×64 PNG country flags (`esp.png`, `ita.png`, `usa.png`, etc.)
    └── lib/                    ← Vendored Python HTTP dependencies (`requests`, `urllib3`, `certifi`, `idna`, `charset_normalizer`)
```

---

## 4. API Endpoints & Data Nuances

### 4.1 Match Scoreboard (`atp.py`) & Tournament Draw (`atp_tournament.py`)
1. **Primary Endpoint (ESPN ATP Scoreboard)**:
   ```http
   GET https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard
   ```
   - Returns `events[]` (each active tournament this week, e.g., `Rolex Paris Masters`, `Bybit Stockholm Open`).
   - Inside each event, `groupings[]` separates `"mens-singles"` (`grouping.slug == "mens-singles"`) and `"mens-doubles"` (`grouping.slug == "mens-doubles"`).
2. **Live Point & Serve Enrichment (Official ATP Live Gateway)**:
   ```http
   GET https://app.atptour.com/api/v2/gateway/livematches/website?scoringTournamentLevel=tour
   ```
   - Polled alongside the scoreboard when live matches are active.
   - Provides in-game point score (`GameScore`: `15`, `30`, `40`, `AD`), active server (`ServerTeam`), and match duration (`MatchTimeTotal`: `"01:26:12"`).
3. **Set Linescore Formatting**:
   - Reads `competitor["linescores"]` (`[{"value": 6.0, "winner": true}, {"value": 7.0, "tiebreak": 7, "winner": true}]`).
   - Formats tiebreaks cleanly using standard tennis notation: `7-6(5)` (showing the losing tiebreak score in parentheses).
4. **Row Display Format**:
   - **Tournament Section Header (`valid: false`)**:
     - *Title*: `── 🏆 Rolex Paris Masters (Paris, France · Men's Singles) ──`
     - *Subtitle*: `Filter: atp live · atp doubles · atp qual · atp {player} · Full draw: atpt`
   - **Live Match (`state == "in"`)**:
     - *Title*: `🔴 🇪🇸 [2] C. Alcaraz  6-4, 3-2 (40-15*)  vs  🇺🇸 [3] B. Shelton  —  Set 2`
     - *Subtitle*: `Rolex Paris Masters · Final · Court Central · 1h 18m`
   - **Upcoming Match (`state == "pre"`)**:
     - *Title*: `🇪🇸 [2] C. Alcaraz  vs  🇺🇸 [3] B. Shelton  —  Sun 9:00 AM`
     - *Subtitle*: `Rolex Paris Masters · Final · Court Central`
   - **Completed Match (`state == "post"`, Winner Listed First with `d.`)**:
     - *Title*: `🇪🇸 [2] C. Alcaraz  d.  🇳🇴 C. Ruud   6-4, 6-4  —  Final`
     - *Subtitle*: `Rolex Paris Masters · Semifinal · Court Central`
   - **Icon**: Composite 64×64 dual-flag icon `matchup_{ioc1}_{ioc2}.png` (e.g., `matchup_esp_usa.png`).
   - **Modifiers**:
     - `Enter`: Open Tournament Match Center / Scoreboard URL.
     - `⌘` (Cmd): Open Player 1's ATP Player Card (`⌘ Open Carlos Alcaraz Player Profile`).
     - `⌥` (Alt): Open Player 2's ATP Player Card (`⌥ Open Ben Shelton Player Profile`).

### 4.2 World Rankings (`atp_rankings.py`)
```http
GET https://site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings
```
- Returns Top 150 ATP Singles players in `rankings[0]["ranks"]`.
- **Fields**: `current` (1–150), `previous`, `points` (`9550.0`), `trend` (`"+1"`, `"-2"`, `"-"`), `athlete.displayName`, `athlete.citizenshipCountry` (`"GER"`), `athlete.age`, `athlete.birthPlace.summary`, `athlete.headshot`, `athlete.flag`.
- **Row Format**:
  - *Title*: `#1 Alexander Zverev  🇩🇪 GER  —  9,550 pts  (▲1)`
  - *Subtitle*: `Prev: #2  ·  Age: 29  ·  Hamburg, Germany`
  - *Icon*: Cached player headshot `headshots/{athlete_id}.png` (falls back to `flags/{ioc}.png`).
  - *`Enter`*: Sanitized player card URL `https://www.espn.com/tennis/player/_/id/{id}/{slug}`.
  - *`⌘` (Cmd)*: `⌘ Open Player Results & Match Log` (`https://www.espn.com/tennis/player/results/_/id/{id}`).
- **Supported Filters**:
  - Default (`atpr`): Top 50 players.
  - Slice (`atpr top10`, `atpr top25`, `atpr all`): Top 10, Top 25, or all 150 players.
  - Country (`atpr usa`, `atpr ita`, `atpr esp`, `atpr fra`): All Top 150 players matching that country code or country name.
  - Player Name (`atpr sinner`, `atpr shelton`): Direct filter within Top 150.

### 4.3 Full-Season Tour Schedule / Calendar (`atp_schedule.py`)
```http
GET https://www.atptour.com/en/-/tournaments/calendar/tour
```
- Returns `TournamentDates[]` (grouped by month) containing all ~65 ATP Tour & Grand Slam events for the season (~80 KB total).
- **Fields per Tournament**: `Id`, `Name` (`"Rolex Paris Masters"`), `Location` (`"Paris, France"`), `FormattedDate` (`"2 - 8 November, 2026"`), `Type` (`"1000"`, `"500"`, `"250"`, `"GS"`, `"WS"`, `"UC"`, `"LVR"`), `Surface` (`"Hard"`, `"Clay"`, `"Grass"`), `IndoorOutdoor` (`"I"` or `"O"`), `TotalFinancialCommitment` (`"$7,703,855"`), `IsLive`, `IsPastEvent`, `SglDrawUrl`, `ScoresUrl`, `TournamentOverviewUrl`.
- **Grouping & Sorting**:
  1. `── 🔴 Active This Week ──` (`IsLive == true`)
  2. `── 📅 Upcoming ATP Tournaments ──` (`IsPastEvent == false and not IsLive`)
  3. `── ✅ Completed 2026 Tournaments ──` (`IsPastEvent == true`, ordered most-recent first)
- **Row Format**:
  - *Title*: `🔴 Rolex Paris Masters  [Masters 1000]  —  Nov 2–8`
  - *Subtitle*: `Paris, France  ·  Hard (Indoor)  ·  Purse: $7,703,855`
  - *`Enter`*: Open Tournament Overview / Live Scores on `atptour.com`.
  - *`⌘` (Cmd)*: Open Tournament Singles Draw (`https://www.atptour.com{DrawsUrl}`).
  - *`⌥` (Alt)*: Open Tournament Daily Schedule (`https://www.atptour.com{ScheduleUrl}`).

### 4.4 Unified Player Profile, Stats & Recent Matches (`atp_player.py`)
Bridges ESPN's player search/headshots/eventlog with the Official ATP Tour's player hero & season service/return stats endpoints:
1. **ESPN Player Search & Core Profile**:
   ```http
   GET https://site.web.api.espn.com/apis/search/v2?query={query}&limit=6&type=player
   GET https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/athletes/{espn_id}/statistics
   ```
2. **Official ATP Tour Player Code Lookup, Hero & 2026 Stats**:
   ```http
   GET https://www.atptour.com/en/-/ajax/playersearch/PlayerUrlSearch?searchTerm={query}
   GET https://www.atptour.com/en/-/www/players/hero/{atp_code}?v=1
   GET https://www.atptour.com/en/-/www/stats/{atp_code}/{year}/all?v=1
   ```
   - Extracts `atp_code` (e.g., `s0ag` for Jannik Sinner, `a0e2` for Carlos Alcaraz) from `PlayerUrlSearch`.
   - `hero/{atp_code}` returns `SglRank`, `SglHiRank`, `SglYtdWon`, `SglYtdLost`, `SglYtdTitles`, `SglYtdPrizeFormatted`, `SglCareerWon`, `SglCareerLost`, `SglCareerTitles`, `CareerPrizeFormatted`, `Coach`, `PlayHand`, `BackHand`.
   - `stats/{atp_code}/{year}/all` returns `ServiceRecordStats` and `ReturnRecordStats`.
3. **Row 1 (Player Overview & Modifier Stats)**:
   - *Title*: `#2 Jannik Sinner  🇮🇹 ITA  (Age 25 · Right-Handed, Two-Handed BH)`
   - *Default Subtitle*: `2026: 44-3 (6 Titles · $11.59M)  ·  Career: 365-89 (30 Titles · $70.68M)  ·  Career High: #1`
   - *`⌘` (Cmd — 2026 Service Stats)*: `⌘ Serve (2026): 454 Aces · 73 DF · 65% 1st Srv · 81% 1st Won · 59% 2nd Won · 93% Srv Gms Won · 71% BP Saved`
   - *`⌥` (Alt — 2026 Return Stats)*: `⌥ Return (2026): 33% 1st Ret Won · 54% 2nd Ret Won · 29% Ret Gms Won · 41% BP Conv · 56% Total Pts Won`
4. **Rows 2–11 (Inline Recent Match Results when `len(matched_players) == 1`)**:
   ```http
   GET https://sports.core.api.espn.com/v2/sports/tennis/leagues/atp/seasons/{year}/athletes/{espn_id}/eventlog
   ```
   - Resolves the last 10 competition `$ref` items concurrently via `ThreadPoolExecutor(max_workers=8)` and caches the resolved match list for 10 minutes.
   - Displays each match with tournament name, round, opponent rank/seed, W/L indicator, and set linescore (e.g., `✅ W vs [3] B. Shelton  6-4, 7-6(5)  —  Rolex Paris Masters (SF)`).

---

## 5. Caching Strategy (`utils.py`)
- Uses Alfred's `$alfred_workflow_cache` (`~/Library/Caches/com.runningwithcrayons.Alfred/Workflow Data/com.popbot.alfred-atp-tour`).
- Stale-while-revalidate fallback on network errors.
- **TTLs**:
  - Scoreboard & Live Gateway (`atp`): `30` seconds (`"rerun": 5.0` when any displayed match is live)
  - Tournament Draw (`atpt`): `120` seconds (2 minutes)
  - Rankings (`atpr`): `600` seconds (10 minutes)
  - Tour Calendar (`atps`): `3600` seconds (1 hour)
  - Player Stats & Recent Matches (`atpp`): `600` seconds (10 minutes)
  - Player Headshots & Country Flags: `604800` seconds (7 days)
