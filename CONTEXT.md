# ATP Tour Alfred Workflow

An Alfred 5 workflow for tracking men's professional tennis on the ATP Tour—including live and daily tournament match scores, official PIF ATP Rankings, the full-season tournament calendar, tournament draws, and player profiles with current-season service/return statistics and recent match results.

## Language

**ATP Tour**:
The top-tier men's professional tennis circuit organized by the Association of Tennis Professionals, comprising Grand Slams, ATP Masters 1000, ATP 500, ATP 250, the Nitto ATP Finals, and the United Cup (excluding lower-tier ATP Challenger and ITF World Tennis Tour circuits unless explicitly queried).
_Avoid_: Men's tennis, Challenger tour, ITF

**Tournament Tier**:
The official category and ranking-point weight of an event on the calendar: `Grand Slam` (2000), `ATP Finals` (1500), `Masters 1000` (1000), `ATP 500` (500), `ATP 250` (250), or `Team Event` (United Cup / Laver Cup / Davis Cup).
_Avoid_: Division, conference, level

**Grouping (Draw Discipline)**:
A competition division within a tournament event—specifically `Men's Singles` (`mens-singles`, the default scoreboard view) or `Men's Doubles` (`mens-doubles`).
_Avoid_: League, category, bracket

**Smart Active Window**:
The default scoreboard filtering rule when invoking `atp` with no query: displays all currently `Live` matches, all `Today` scheduled/completed matches, and recent Main Draw matches (`Round of 64` through `Final`), omitting completed early-week Qualifying matches unless the tournament is still in its qualifying phase or the user filters by `qual` or `all`.
_Avoid_: Raw tournament dump, full draw dump

**Seed**:
A player's or doubles team's tournament draw placement (`1`–`32`), rendered in square brackets (`[2] C. Alcaraz`) to distinguish a tournament seed from a player's world ranking (`#2`).
_Avoid_: Curated rank, poll rank

**Set Linescore**:
The sequence of games won per set by each competitor (e.g., `6-4, 7-6(5), 6-3`), with tiebreak points rendered in parentheses next to the losing tiebreak game score (`6(5)`) or superscripted.
_Avoid_: Quarters, periods, innings

**Boundary-Aware Subcommand**:
A single-letter command suffix (`r` for Rankings, `s` for Schedule/Calendar, `t` for Tournament Draw, `p` for Player Profile & Stats) attached directly to the base `atp` keyword (`atpr`, `atps`, `atpt`, `atpp`) that only triggers when the suffix is the entire query or is immediately followed by whitespace, preventing collisions with space-separated scoreboard filters (`atp sinner`, `atp paris`, `atp roland garros`).
_Avoid_: Prefix route, raw prefix

**Unified Player View**:
The response layout when `atpp {player}` resolves to a single ATP player: Row 1 displays the player's World Rank, YTD & Career W-L record, Titles, and Prize Money (with `⌘` Service Stats and `⌥` Return Stats from the official ATP stats API), and Rows 2+ display the player's recent tournament match results inline.
_Avoid_: Separate player schedule tab
