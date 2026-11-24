# User guide

What works today, and what to do when it does not. Panel-by-panel guides are
added as panels land; the plan keeps them in this directory.

## Install

From the repository root:

```bash
./setup.sh            # diagnose, install, verify, print the launch command
./setup.sh --check    # diagnose only; change nothing
./setup.sh --run      # set up, then open the workspace
```

The bootstrap targets Linux, Python 3.14+ and [uv](https://docs.astral.sh/uv/).
It never uses `sudo`; missing system libraries are reported with the exact
package-manager command. Optional extras: `--with-ml`, `--with-train`,
`--with-gpu`, `--with-ann`, `--all`.

## Start the workspace

```bash
uv run chess-obs ui
```

The current window is the Phase 0 shell: it confirms Qt, fonts and the launch
path work. The designed workspace (docks, board, panels, 20 themes) arrives in
Phase 6.

## Check the installation

```bash
uv run chess-obs doctor          # human-readable report
uv run chess-obs doctor --json   # machine-readable, for bug reports
```

Exit code `0` means no problems. Warnings (no reference engine installed, no
display in a headless session) do not block CLI use.

## Configuration

The file lives at `~/.config/chess-observatory/config.toml` (or
`$XDG_CONFIG_HOME/chess-observatory/config.toml`).

```bash
uv run chess-obs config show            # effective values
uv run chess-obs config show --json     # values plus which layer set them
uv run chess-obs config path            # where the file is
uv run chess-obs --config my.toml config show
uv run chess-obs ui --set ui.theme=midnight
```

Precedence: built-in defaults → user file → environment → CLI. Environment names
are mechanical: `ui.theme` becomes `CHESS_OBS_UI_THEME`.

Example file:

```toml
config_version = 1

[app]
log_level = "INFO"

[ui]
theme = "observatory-dark"
board_palette = "classic-green"
density = "comfortable"
motion = true

[search]
threads = 1
hash_mb = 256

[ml]
enabled = false
```

Unknown keys and invalid values are errors, not silent fallbacks.

## Logs

Rotating logs live at `~/.local/state/chess-observatory/logs/chess-observatory.log`
(three backups, 2 MB each). `chess-obs doctor` reports the exact directory.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `chess-obs: command not found` | Run through uv: `uv run chess-obs …`, or `uv sync` first. |
| Qt fails to start / plugin error | Install the Qt runtime libraries; `./setup.sh` prints the exact `apt`/`dnf`/`pacman` line. |
| Headless server | Use `chess-obs doctor` and other CLI commands; the GUI needs a display, or `QT_QPA_PLATFORM=offscreen` for tests. |
| `doctor` says the package is missing | `uv sync` in the repository root. |
| Config seems ignored | `chess-obs config show --json` shows the effective value and its source. |
| Need the full diagnosis | `uv run chess-obs doctor --json > report.json` and attach it to an issue. |
