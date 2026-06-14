#!/usr/bin/env bash
# Install the aasm-riscos VS Code extension as a symlink under VS Code's
# extensions directory, so edits to the grammar in this repo are picked up
# on the next VS Code reload (no rebuild step).
#
# Usage:
#   ./install.sh                              # standard VS Code (~/.vscode/extensions)
#   ./install.sh --target <extensions-dir>    # custom extensions dir (Code-OSS, Flatpak, code-server)
#   ./install.sh --uninstall                  # remove the symlink
#
# Idempotent — safe to run multiple times.

set -euo pipefail

EXTENSION_NAME="local.aasm-riscos-0.1.0"
TARGET_DIR="${HOME}/.vscode/extensions"
UNINSTALL=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            TARGET_DIR="$2"
            shift 2
            ;;
        --uninstall)
            UNINSTALL=1
            shift
            ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LINK_PATH="${TARGET_DIR}/${EXTENSION_NAME}"

if [[ $UNINSTALL -eq 1 ]]; then
    if [[ -L "$LINK_PATH" ]]; then
        rm "$LINK_PATH"
        echo "Removed $LINK_PATH"
    elif [[ -e "$LINK_PATH" ]]; then
        echo "Refusing to remove $LINK_PATH — it is not a symlink." >&2
        exit 1
    else
        echo "Nothing to remove at $LINK_PATH"
    fi
    echo "Reload VS Code to drop the language registration."
    exit 0
fi

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Creating $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
fi

if [[ -L "$LINK_PATH" ]]; then
    # already a symlink — check it points where we expect
    current_target="$(readlink "$LINK_PATH")"
    if [[ "$current_target" == "$SCRIPT_DIR" ]]; then
        echo "Already installed: $LINK_PATH -> $SCRIPT_DIR"
        echo "Nothing to do."
        exit 0
    fi
    echo "Replacing existing symlink at $LINK_PATH (was -> $current_target)"
    rm "$LINK_PATH"
elif [[ -e "$LINK_PATH" ]]; then
    echo "Refusing to overwrite $LINK_PATH — a non-symlink already exists there." >&2
    echo "Move or delete it manually and re-run." >&2
    exit 1
fi

ln -s "$SCRIPT_DIR" "$LINK_PATH"
echo "Installed: $LINK_PATH -> $SCRIPT_DIR"
echo
echo "Reload VS Code (Ctrl-Shift-P -> 'Developer: Reload Window') and open"
echo "a RISC OS source file (e.g. external/Kernel/s/NewReset) to see the"
echo "syntax highlighting take effect."
