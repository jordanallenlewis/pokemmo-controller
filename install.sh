#!/bin/sh
# PokeMMO controller layout: one-command setup for macOS and Linux (Steam Deck too).
#   curl -fsSL https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/install.sh | sh
# Undo:
#   curl -fsSL https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/install.sh | sh -s -- --uninstall
# Nothing to install first. Downloads this project (and, only if Python 3.9+ is
# missing, a private copy of Python via uv) into a temp folder, runs
# tools/setup.py, then deletes the temp folder. Extra options go to setup.py:
# --uninstall, --no-wheel, --switch-positional.
set -eu

REPO=jordanallenlewis/pokemmo-controller
TMP=$(mktemp -d 2>/dev/null || mktemp -d -t pokemmo-controller)
trap 'rm -rf "$TMP"' EXIT INT TERM

echo "Downloading pokemmo-controller..."
SRC=${POKEMMO_CONTROLLER_SRC:-https://github.com/$REPO/archive/refs/heads/main.tar.gz}
curl -fsSL "$SRC" | tar -xz -C "$TMP"
SETUP=$(find "$TMP" -path '*/tools/setup.py' | head -n 1)

have_python() {
    # macOS ships a python3 stub that pops an install dialog without the developer tools.
    if [ "$(uname -s)" = Darwin ] && [ "$(command -v python3)" = /usr/bin/python3 ] \
        && ! xcode-select -p >/dev/null 2>&1; then
        return 1
    fi
    command -v python3 >/dev/null 2>&1 &&
        python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null
}

if have_python; then
    python3 "$SETUP" "$@"
else
    echo "Python not found: fetching a private copy just for this run..."
    case "$(uname -m)" in
        arm64|aarch64) ARCH=aarch64 ;;
        *) ARCH=x86_64 ;;
    esac
    if [ "$(uname -s)" = Darwin ]; then TARGET=$ARCH-apple-darwin; else TARGET=$ARCH-unknown-linux-gnu; fi
    mkdir -p "$TMP/uv"
    curl -fsSL "https://github.com/astral-sh/uv/releases/latest/download/uv-$TARGET.tar.gz" \
        | tar -xz -C "$TMP/uv" --strip-components 1
    UV_CACHE_DIR="$TMP/uv-cache" UV_PYTHON_INSTALL_DIR="$TMP/uv-python" \
        "$TMP/uv/uv" run --quiet --no-project --python 3.12 "$SETUP" "$@"
fi
