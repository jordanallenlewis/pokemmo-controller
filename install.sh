#!/bin/sh
# PokeMMO controller layout: one-command setup for macOS and Linux (Steam Deck too).
# Install, or update to the newest version (run it again any time):
#   curl -fsSL https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/install.sh | sh
# Undo:
#   curl -fsSL https://raw.githubusercontent.com/jordanallenlewis/pokemmo-controller/main/install.sh | sh -s -- --uninstall
# Nothing to install first. Downloads this project (and, only if Python 3.9+ is
# missing, a private copy of Python via uv) into a temp folder, runs
# tools/setup.py, then deletes the temp folder. Extra options go to setup.py:
# --uninstall, --no-wheel, --switch-positional, --ui, --install-ui, --dry-run. POSIX sh: works under dash,
# bash and zsh.
set -eu

REPO=jordanallenlewis/pokemmo-controller
TMP=$(mktemp -d 2>/dev/null || mktemp -d -t pokemmo-controller)
trap 'rm -rf "$TMP"' EXIT
trap 'rm -rf "$TMP"; exit 130' INT TERM

fetch() { # fetch <url or local file> <output file>
    case $1 in
        http://* | https://*) curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 20 -o "$2" "$1" ;;
        *) cp "$1" "$2" ;;
    esac
}

echo "PokeMMO Controller is an unofficial, fan-made tool, made by and for PokeMMO players. It is not made, endorsed or supported by the PokeMMO team."
echo "Downloading pokemmo-controller..."
SRC=${POKEMMO_CONTROLLER_SRC:-https://github.com/$REPO/archive/refs/heads/main.tar.gz}
if ! fetch "$SRC" "$TMP/src.tar.gz" || ! tar -xzf "$TMP/src.tar.gz" -C "$TMP"; then
    echo "Could not download $SRC. Check your internet connection and try again." >&2
    exit 1
fi
SETUP=$(find "$TMP" -path '*/tools/setup.py' | head -n 1)
if [ -z "$SETUP" ]; then
    echo "The download was incomplete (no tools/setup.py). Try again." >&2
    exit 1
fi

have_python() {
    [ "${POKEMMO_CONTROLLER_FORCE_UV:-}" = 1 ] && return 1
    # macOS ships a python3 stub that pops an install dialog without the developer tools.
    if [ "$(uname -s)" = Darwin ] && [ "$(command -v python3)" = /usr/bin/python3 ] \
        && ! xcode-select -p >/dev/null 2>&1; then
        return 1
    fi
    command -v python3 >/dev/null 2>&1 &&
        python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null
}

# </dev/null: under `curl | sh` stdin is this script, which nothing else may read.
if have_python; then
    python3 "$SETUP" ${1+"$@"} </dev/null
else
    echo "Python not found: fetching a private copy just for this run..."
    case "$(uname -m)" in
        arm64 | aarch64) ARCH=aarch64 ;;
        *) ARCH=x86_64 ;;
    esac
    if [ "$(uname -s)" = Darwin ]; then TARGET=$ARCH-apple-darwin; else TARGET=$ARCH-unknown-linux-gnu; fi
    mkdir -p "$TMP/uv"
    if ! fetch "https://github.com/astral-sh/uv/releases/latest/download/uv-$TARGET.tar.gz" "$TMP/uv.tar.gz" \
        || ! tar -xzf "$TMP/uv.tar.gz" -C "$TMP/uv" --strip-components 1; then
        echo "Could not download uv (a private Python). Check your internet connection, or install Python 3.9+." >&2
        exit 1
    fi
    UV_CACHE_DIR="$TMP/uv-cache" UV_PYTHON_INSTALL_DIR="$TMP/uv-python" \
        "$TMP/uv/uv" run --quiet --no-project --no-config --python 3.12 "$SETUP" ${1+"$@"} </dev/null
fi
