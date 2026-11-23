# Chess Observatory

Go ahead, be a chess nerd.

A computational chess research workstation: an instrument for *why* a position
works, not just who is winning.

## Quick start

```bash
./setup.sh            # diagnose, install, verify, and print the launch command
./setup.sh --check    # diagnose only; change nothing
./setup.sh --run      # set up, then open the workspace
```

The bootstrap targets Linux, Python 3.14+, and [uv](https://docs.astral.sh/uv/).
It never uses `sudo`; missing system libraries are reported with the exact
package-manager command. Optional extras: `--with-ml`, `--with-train`,
`--with-gpu`, `--with-ann`, or `--all`.

When it finishes, start the workspace with:

```bash
uv run chess-obs ui
```

Everything works with machine learning disabled. See `planning_docs/` for the
implementation plan and design decisions.
