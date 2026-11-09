# Use Boundary-Aware Subcommand Routing for Tennis Modules

Status: accepted

We will configure a single Script Filter (`keyword: atp`, `withspace: false`) in `info.plist` invoking `python3 atp.py "$1"`, and route to subcommands (`r` Rankings, `s` Schedule/Calendar, `t` Tournament Draw, `p` Player Stats & Recent Matches) only when the subcommand character has no leading space and is either the entire query or immediately followed by whitespace.

## Context & Trade-offs

Users need to filter the live/daily scoreboard by typing a space followed by a player name, tournament city, surface, or round (`atp sinner`, `atp paris`, `atp trace`, `atp sf`, `atp live`). Naive prefix matching after `.strip()` would misroute `atp sinner` (`"sinner"`) to Schedule (`atps inner`), `atp shelton` to `atps helton`, `atp taylor` to Tournament (`atpt aylor`), and `atp paul` to Player (`atpp aul`).

## Consequences

- Typing a space after `atp` (`raw_query.startswith(" ")`, e.g., `atp sinner`, `atp paris`, `atp doubles`, `atp live`) always routes to the **Scoreboard (`atp.py`)** as a filter.
- Typing a suffix directly attached to `atp` (`atpr`, `atpr top10`, `atps`, `atps clay`, `atpt paris`, `atpp sinner`) routes cleanly to the corresponding module without collisions.
