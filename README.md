# 🎾 ATP Tour — Alfred 5 Workflow

Track **Men's ATP Tour** live and daily tournament match scores, official PIF ATP Singles Rankings, the full-season tournament calendar, tournament draws, and player profiles with current-season Service & Return statistics and recent match results directly inside Alfred 5.

## Features
- **Hybrid Zero-Auth API Architecture**: Combines ESPN's public tennis API (scoreboards, Top 150 rankings, player headshots, country flags, match eventlogs) with the official ATP Tour JSON endpoints (`atptour.com` & `app.atptour.com` for the full-season tournament calendar, live point-by-point scores, 2026 YTD W-L/Titles/Prize, and 2026 Service & Return stats).
- **Smart Active Window Scoreboard (`atp`)**: Displays live matches first, then today's upcoming/completed matches and recent Main Draw matches (`Singles` default), with standard tennis set linescores (`6-4, 7-6(5)`) and dual country-flag matchup icons.
- **Official PIF ATP Rankings (`atpr`)**: Top 50 Singles default with instant filters for `atpr top10`, `atpr top25`, `atpr all` (Top 150), country codes (`atpr usa`, `atpr ita`, `atpr esp`), or player names (`atpr sinner`).
- **Full-Season Tournament Calendar (`atps`)**: Complete ATP Tour & Grand Slam calendar grouped into `Active This Week`, `Upcoming`, and `Completed`, with tier badges (`Grand Slam`, `ATP Masters 1000`, `ATP 500`, `ATP 250`), surface, indoor/outdoor, draw sizes, and prize money.
- **Tournament Draw Viewer (`atpt`)**: Browse the full round-by-round Main Draw (`Final` → `Semifinal` → `Quarterfinal` → `R16` → `R32` → `R64`), plus `atpt doubles` and `atpt qual`.
- **Unified Player View (`atpp {player}`)**: Row 1 displays World Rank, 2026 YTD & Career W-L/Titles/Prize, **`⌘` 2026 Service Stats** (Aces, DF, 1st Serve %, 1st/2nd Serve Won %, Service Games Won %, BP Saved %), and **`⌥` 2026 Return Stats** (1st/2nd Return Won %, Return Games Won %, BP Converted %, Total Points Won %); Rows 2–11 display the player's last 10 tournament matches inline.
- **Zero Dependencies**: Bundled `requests` in `lib/` and pure-Python PNG compositing in `image_utils.py`.

## Usage

| Command | Description |
| :--- | :--- |
| `atp` | Active ATP tournament scores (Live → Upcoming → Final, Singles default) |
| `atp alcaraz` / `atp paris` | Filter active scoreboard by player or tournament |
| `atp doubles` / `atp live` / `atp all` | View Doubles matches, Live matches only, or full tournament draw |
| `atpr` / `atpr top10` / `atpr all` | View Top 50, Top 10, or Top 150 PIF ATP Singles Rankings |
| `atpr usa` / `atpr ita` / `atpr esp` | Filter Top 150 rankings by country |
| `atps` / `atps slam` / `atps 1000` / `atps clay` | View full-season ATP Tour calendar or filter by tier/surface/city/month |
| `atpt` / `atpt doubles` | View full round-by-round tournament draw for active ATP events |
| `atpp sinner` / `atpp alcaraz` | View player rank, YTD & Career W-L/Titles/Prize (`⌘` Serve, `⌥` Return) + last 10 matches |

## Building
```bash
python3 build.py
```
Creates `ATP Tour.alfredworkflow`. Double-click to install in Alfred 5.
