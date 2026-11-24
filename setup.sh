#!/usr/bin/env bash
# =============================================================================
# Chess Observatory — environment bootstrap
# =============================================================================
# Run from the repository root (or anywhere; it locates itself):
#
#     ./setup.sh                 # set up, verify, print the start command
#     ./setup.sh --check         # diagnose only, change nothing
#     ./setup.sh --with-ml       # also install ML inference (onnxruntime)
#     ./setup.sh --with-train    # also install training (torch)
#     ./setup.sh --with-gpu      # also install GPU providers
#     ./setup.sh --with-ann      # also install the ANN index (faiss-cpu)
#     ./setup.sh --run           # set up, then launch the workspace
#
# Design rules:
#   * Linux only (the project targets X11 + Wayland).
#   * Never uses sudo, never edits system files, never deletes user data.
#   * Idempotent: safe to run as many times as you like.
#   * Every failure names the problem and the exact command that fixes it.
# =============================================================================

set -Eeuo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Constants and output helpers
# ---------------------------------------------------------------------------
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

MIN_PY_MAJOR=3
MIN_PY_MINOR=14
UV_INSTALL_URL="https://astral.sh/uv/install.sh"

CHECK_ONLY=0
ASSUME_YES=0
RUN_AFTER=0
EXTRA_ML=0
EXTRA_TRAIN=0
EXTRA_GPU=0
EXTRA_ANN=0
FAILURES=0
WARNINGS=0

if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_CYAN=$'\033[36m'
else
    C_RESET=""; C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""
    C_YELLOW=""; C_CYAN=""
fi

say()  { printf '%s\n' "$*"; }
step() { printf '\n%s==>%s %s%s%s\n' "$C_CYAN" "$C_RESET" "$C_BOLD" "$*" "$C_RESET"; }
ok()   { printf '  %s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '  %s!%s %s\n' "$C_YELLOW" "$C_RESET" "$*"; WARNINGS=$((WARNINGS + 1)); }
fail() { printf '  %s✗%s %s\n' "$C_RED" "$C_RESET" "$*"; FAILURES=$((FAILURES + 1)); }
hint() { printf '    %s%s%s\n' "$C_DIM" "$*" "$C_RESET"; }

die() {
    printf '\n%sERROR:%s %s\n' "$C_RED" "$C_RESET" "$*" >&2
    exit 1
}

on_error() {
    local exit_code=$?
    printf '\n%sUnexpected failure%s at line %s (exit %s).\n' \
        "$C_RED" "$C_RESET" "${BASH_LINENO[0]:-?}" "$exit_code" >&2
    printf 'Re-run with %s--check%s for a diagnosis, or open an issue with this output.\n' \
        "$C_BOLD" "$C_RESET" >&2
    exit "$exit_code"
}
trap on_error ERR

usage() {
    cat <<'EOF'
Chess Observatory — environment bootstrap

Usage: ./setup.sh [options]

Options:
  --check           Diagnose only; install nothing, change nothing.
  --with-ml         Install the [ml] extra (onnxruntime inference).
  --with-train      Install the [train] extra (torch, training only).
  --with-gpu        Install the [gpu] extra (CUDA/ROCm providers).
  --with-ann        Install the [ann] extra (faiss-cpu similarity index).
  --all             Install every optional extra above.
  --run             Launch the workspace after a successful setup.
  -y, --yes         Assume "yes" for interactive prompts.
  -h, --help        Show this help and exit.

The script checks: Linux, Python >= 3.14, uv, Qt/X11 system libraries,
optional GPU, display server, project files, and the installed packages.
It prints the exact command to start the program when it finishes.
EOF
}

while (($#)); do
    case "$1" in
        --check)        CHECK_ONLY=1 ;;
        --with-ml)      EXTRA_ML=1 ;;
        --with-train)   EXTRA_TRAIN=1 ;;
        --with-gpu)     EXTRA_GPU=1 ;;
        --with-ann)     EXTRA_ANN=1 ;;
        --all)          EXTRA_ML=1; EXTRA_TRAIN=1; EXTRA_GPU=1; EXTRA_ANN=1 ;;
        --run)          RUN_AFTER=1 ;;
        -y|--yes)       ASSUME_YES=1 ;;
        -h|--help)      usage; exit 0 ;;
        *)              die "Unknown option: $1 (try --help)" ;;
    esac
    shift
done

ask() {
    # ask "<question>" -> 0 for yes
    local question=$1
    if ((ASSUME_YES)); then
        return 0
    fi
    if [[ ! -t 0 ]]; then
        return 1
    fi
    local reply=""
    printf '%s%s%s %s[Y/n]%s ' "$C_BOLD" "$question" "$C_RESET" "$C_DIM" "$C_RESET"
    read -r reply || true
    case "${reply,,}" in
        ""|y|yes) return 0 ;;
        *)        return 1 ;;
    esac
}

# ---------------------------------------------------------------------------
# 1. Operating system
# ---------------------------------------------------------------------------
step "Operating system"
if [[ "$(uname -s)" != "Linux" ]]; then
    fail "This project targets Linux only (found: $(uname -s))."
    hint "Windows and macOS are intentionally unsupported (see the plan, D9)."
    exit 1
fi

DISTRO_ID="unknown"; DISTRO_LIKE=""
if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    DISTRO_ID=$(. /etc/os-release; printf '%s' "${ID:-unknown}")
    # shellcheck disable=SC1091
    DISTRO_LIKE=$(. /etc/os-release; printf '%s' "${ID_LIKE:-}")
fi
ok "Linux (${DISTRO_ID}${DISTRO_LIKE:+, like ${DISTRO_LIKE}})"

# ---------------------------------------------------------------------------
# 2. Python
# ---------------------------------------------------------------------------
step "Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+"
PYTHON_BIN=""
for candidate in "${PYTHON:-}" python3.14 python3; do
    [[ -z "$candidate" ]] && continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (${MIN_PY_MAJOR}, ${MIN_PY_MINOR}) else 1)" 2>/dev/null; then
        PYTHON_BIN=$candidate
        break
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    fail "No Python >= ${MIN_PY_MAJOR}.${MIN_PY_MINOR} found."
    hint "Ubuntu/Debian: sudo apt install python${MIN_PY_MAJOR}.${MIN_PY_MINOR}"
    hint "Fedora:        sudo dnf install python${MIN_PY_MAJOR}.${MIN_PY_MINOR}"
    hint "Arch:          sudo pacman -S python"
    hint "Or install uv, which can fetch a suitable Python automatically."
else
    ok "Found $("$PYTHON_BIN" -c 'import sys; print(sys.executable)') ($("$PYTHON_BIN" -V 2>&1))"
fi

# ---------------------------------------------------------------------------
# 3. uv
# ---------------------------------------------------------------------------
step "uv (Python project manager)"
if command -v uv >/dev/null 2>&1; then
    ok "Found $(uv --version 2>/dev/null | head -n1)"
elif ((CHECK_ONLY)); then
    fail "uv is not installed."
    hint "Install it: curl -LsSf ${UV_INSTALL_URL} | sh"
else
    warn "uv is not installed."
    hint "Official installer: curl -LsSf ${UV_INSTALL_URL} | sh"
    if ask "Install uv now from astral.sh?"; then
        if command -v curl >/dev/null 2>&1; then
            curl -LsSf "$UV_INSTALL_URL" | sh
            export PATH="${HOME}/.local/bin:${PATH}"
            hash -r
            if command -v uv >/dev/null 2>&1; then
                ok "uv installed ($(uv --version | head -n1))"
                # Remove the failure counter bump if warn() was counted.
                WARNINGS=$((WARNINGS > 0 ? WARNINGS - 1 : 0))
            else
                fail "uv installed but not on PATH. Add ~/.local/bin to PATH and re-run."
            fi
        else
            fail "curl is not available; install curl or install uv manually."
            hint "https://docs.astral.sh/uv/getting-started/installation/"
        fi
    else
        fail "uv is required. Re-run and accept the install, or install it manually."
    fi
fi

# ---------------------------------------------------------------------------
# 4. Qt / X11 / Wayland system libraries
# ---------------------------------------------------------------------------
step "Qt runtime libraries"
# library -> Debian/Ubuntu package -> Fedora -> Arch
SYSTEM_LIBS=(
    "libGL.so.1:libgl1:mesa-libGL:mesa"
    "libEGL.so.1:libegl1:mesa-libEGL:mesa"
    "libxkbcommon.so.0:libxkbcommon0:libxkbcommon:libxkbcommon"
    "libxcb-cursor.so.0:libxcb-cursor0:xcb-util-cursor:libxcb-cursor"
    "libfontconfig.so.1:fontconfig:fontconfig:fontconfig"
    "libfreetype.so.6:libfreetype6:freetype:freetype2"
    "libdbus-1.so.3:libdbus-1-3:dbus-libs:dbus"
)

# Read the loader cache once. Do not pipe into `grep -q`: with pipefail, grep
# exits early, ldconfig gets SIGPIPE, and every library looks missing.
LD_CACHE=$(ldconfig -p 2>/dev/null || true)

have_lib() {
    grep -Fq -- "$1" <<<"$LD_CACHE"
}

missing_debian=(); missing_fedora=(); missing_arch=()
for entry in "${SYSTEM_LIBS[@]}"; do
    IFS=':' read -r lib debian fedora arch <<<"$entry"
    if have_lib "$lib"; then
        :
    else
        missing_debian+=("$debian")
        missing_fedora+=("$fedora")
        missing_arch+=("$arch")
    fi
done

if ((${#missing_debian[@]} == 0)); then
    ok "All Qt runtime libraries present"
else
    missing_debian_str="${missing_debian[*]}"; missing_debian_str="${missing_debian_str//$'\n'/ }"
    missing_fedora_str="${missing_fedora[*]}"; missing_fedora_str="${missing_fedora_str//$'\n'/ }"
    missing_arch_str="${missing_arch[*]}"; missing_arch_str="${missing_arch_str//$'\n'/ }"
    fail "Missing ${#missing_debian[@]} Qt runtime librar(y/ies): ${missing_debian_str}"
    hint "These are system packages; installing them needs sudo (not done here)."
    case "$DISTRO_ID $DISTRO_LIKE" in
        *debian*|*ubuntu*)  hint "sudo apt install ${missing_debian_str}" ;;
        *fedora*|*rhel*)    hint "sudo dnf install ${missing_fedora_str}" ;;
        *arch*|*manjaro*)   hint "sudo pacman -S ${missing_arch_str}" ;;
        *)                  hint "Install the equivalents of: ${missing_debian_str}" ;;
    esac
fi

# ---------------------------------------------------------------------------
# 5. Display server
# ---------------------------------------------------------------------------
step "Display server"
if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
    ok "Wayland (${WAYLAND_DISPLAY})"
elif [[ -n "${DISPLAY:-}" ]]; then
    ok "X11 (${DISPLAY})"
else
    warn "No DISPLAY or WAYLAND_DISPLAY set (headless session?)."
    hint "The GUI needs a graphical session; CLI commands work headless."
fi

# ---------------------------------------------------------------------------
# 6. Optional GPU
# ---------------------------------------------------------------------------
step "Optional GPU (informational)"
GPU_FOUND=0
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    ok "NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)"
    GPU_FOUND=1
fi
if [[ -r /sys/module/amdgpu/version ]] || command -v rocminfo >/dev/null 2>&1; then
    ok "AMD GPU (ROCm stack detected)"
    GPU_FOUND=1
fi
if ((GPU_FOUND == 0)); then
    say "  ${C_DIM}No GPU detected. CPU inference is the default and is fully supported.${C_RESET}"
fi

# ---------------------------------------------------------------------------
# 7. Project files
# ---------------------------------------------------------------------------
step "Project files"
if [[ ! -f pyproject.toml ]]; then
    fail "pyproject.toml not found in ${SCRIPT_DIR}"
    hint "This repository has not been scaffolded yet (plan Phase 0, step 2)."
    hint "Once it exists, re-run ./setup.sh"
    exit 1
fi
ok "pyproject.toml found"

if [[ -f uv.lock ]]; then
    ok "uv.lock found (dependencies pinned)"
else
    warn "uv.lock missing; it will be generated on first sync."
fi

# PySide6 and numpy are the runtime baseline; check whether the project
# actually declares them, so an early skeleton does not fail verification.
DECLARES_QT=0
if grep -qiE 'pyside6|pyside' pyproject.toml; then DECLARES_QT=1; fi

# ---------------------------------------------------------------------------
# 8. Install
# ---------------------------------------------------------------------------
if ((CHECK_ONLY)); then
    step "Install (skipped: --check)"
else
    step "Installing dependencies with uv sync"
    SYNC_ARGS=(sync)
    ((EXTRA_ML))    && SYNC_ARGS+=(--extra ml)
    ((EXTRA_TRAIN)) && SYNC_ARGS+=(--extra train)
    ((EXTRA_GPU))   && SYNC_ARGS+=(--extra gpu)
    ((EXTRA_ANN))   && SYNC_ARGS+=(--extra ann)

    if uv "${SYNC_ARGS[@]}"; then
        ok "Environment ready at ${SCRIPT_DIR}/.venv"
    else
        fail "uv sync failed."
        hint "Run 'uv sync -v' to see the full resolver output."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# 9. Verify
# ---------------------------------------------------------------------------
step "Verifying the installation"
verify_python() {
    uv run python - <<'PY'
import sys
print(f"  python  {sys.version.split()[0]}  ({sys.executable})")
PY
}

if ((CHECK_ONLY)); then
    say "  ${C_DIM}Skipping package verification (--check).${C_RESET}"
else
    if verify_python; then ok "Interpreter works"; else fail "Interpreter cannot run through uv"; fi

    if ((DECLARES_QT)); then
        if uv run python -c "import PySide6; print(f'  PySide6 {PySide6.__version__}')" 2>/dev/null; then
            ok "PySide6 imports"
        else
            fail "PySide6 is declared but not importable."
            hint "Try: uv sync --reinstall"
        fi
    else
        warn "PySide6 is not declared in pyproject.toml yet (expected before Phase 0 finishes)."
    fi

    if uv run python -c "import numpy; print(f'  numpy   {numpy.__version__}')" 2>/dev/null; then
        ok "numpy imports"
    else
        warn "numpy is not importable yet."
    fi

    if ((EXTRA_ML)); then
        if uv run python -c "import onnxruntime; print(f'  onnxruntime {onnxruntime.__version__}')" 2>/dev/null; then
            ok "onnxruntime imports"
        else
            fail "The [ml] extra did not install onnxruntime."
        fi
    fi
fi

# ---------------------------------------------------------------------------
# 10. Application self-check (best effort until the CLI exists)
# ---------------------------------------------------------------------------
step "Application self-check"
if ((CHECK_ONLY)); then
    say "  ${C_DIM}Skipping (--check).${C_RESET}"
elif uv run chess-obs doctor >/dev/null 2>&1; then
    uv run chess-obs doctor | sed 's/^/  /'
    ok "doctor passed"
elif uv run python -c "import chess_observatory" >/dev/null 2>&1; then
    warn "Package imports, but 'chess-obs doctor' is not available yet."
    hint "Expected until Phase 0 step 11 lands."
else
    warn "The package is not importable yet."
    hint "Expected before the core scaffolding lands; re-run ./setup.sh afterwards."
fi

# ---------------------------------------------------------------------------
# 11. Summary and start command
# ---------------------------------------------------------------------------
step "Summary"
if ((FAILURES > 0)); then
    printf '  %s%d problem(s)%s, %d warning(s). Fix the items marked ✗ and re-run.\n' \
        "$C_RED" "$FAILURES" "$C_RESET" "$WARNINGS"
    exit 1
fi
printf '  %sEnvironment OK%s with %d warning(s).\n' "$C_GREEN" "$C_RESET" "$WARNINGS"

say ""
say "${C_BOLD}Start Chess Observatory${C_RESET}"
say ""
say "    ${C_CYAN}uv run chess-obs ui${C_RESET}"
say ""
say "  Or, to set up and launch in one step next time:"
say "    ${C_DIM}./setup.sh --run${C_RESET}"
say ""
say "${C_BOLD}Useful commands${C_RESET}"
say ""
say "    uv run chess-obs doctor          # full environment diagnosis"
say "    uv run chess-obs config show     # effective configuration and its source"
say "    uv run chess-obs ui              # open the workspace"
say "    uv run chess-obs version         # version and install path"
say ""
say "${C_BOLD}First run${C_RESET}"
say ""
say "  · This is the Phase 0 shell: it verifies Qt, fonts and the launch path."
say "  · The designed workspace, panels and 20 themes arrive in Phase 6."
say "  · Everything works with ML disabled; that is the default."
say ""
say "  Docs: docs/user/  ·  Troubleshooting: uv run chess-obs doctor"
say ""

if ((RUN_AFTER)); then
    step "Launching"
    exec uv run chess-obs ui
fi
