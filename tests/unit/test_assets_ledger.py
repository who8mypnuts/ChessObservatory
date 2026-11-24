"""The asset licence ledger covers every bundled file (plan §13.1, R13)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
LEDGER = ASSETS / "LICENSES.md"
IGNORED = {"LICENSES.md", "README.md"}


def ledger_rows() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0] in {"Path", ""} or set(cells[0]) <= {"-", ":"}:
            continue
        rows[cells[0]] = cells
    return rows


def bundled_files() -> list[Path]:
    files = []
    for path in ASSETS.rglob("*"):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(ASSETS).parts):
            continue
        if path.name in IGNORED:
            continue
        files.append(path)
    return files


def test_ledger_exists() -> None:
    assert LEDGER.is_file()


def test_every_bundled_file_is_listed() -> None:
    rows = ledger_rows()
    missing = [
        str(path.relative_to(ASSETS))
        for path in bundled_files()
        if str(path.relative_to(ASSETS)) not in rows
    ]
    assert not missing, f"unlisted asset(s): {', '.join(sorted(missing))}"


def test_every_listed_file_exists_and_is_complete() -> None:
    for relative, cells in ledger_rows().items():
        assert (ASSETS / relative).is_file(), f"ledger lists a missing file: {relative}"
        assert len(cells) >= 5, f"row for {relative} needs 5 columns"
        path, kind, licence, source, _attribution = cells[:5]
        assert path == relative
        assert kind, f"{relative}: kind is empty"
        assert licence, f"{relative}: licence is empty"
        assert source, f"{relative}: source is empty"


def test_ledger_has_no_duplicate_paths() -> None:
    paths = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and cells[0] not in {"Path", ""} and not set(cells[0]) <= {"-", ":"}:
                paths.append(cells[0])
    assert len(paths) == len(set(paths))
