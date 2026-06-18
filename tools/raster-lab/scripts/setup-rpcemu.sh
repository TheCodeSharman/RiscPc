#!/usr/bin/env bash
# setup-rpcemu.sh
#
# Builds RPCEmu from this repo's vendored source at external/rpcemu/ and
# symlinks a pristine RISC OS ROM into the emulator's roms/ directory.
#
# The source under external/rpcemu/ is RPCEmu mainline 0.9.5 (tag
# rpcemu-v0.9.5-import) plus any local patches in this repo's git history.
# We do an out-of-tree build under $RPCEMU_BUILD_DIR so the vendored
# source stays clean (no build artifacts to commit by accident).
#
# Tested target: Pop!_OS 24.04 / Ubuntu derivatives.
#
# Stages (each is idempotent; safe to re-run):
#   deps    - install Qt5 + build deps via apt
#   sync    - rsync external/rpcemu/ -> $RPCEMU_BUILD_DIR
#   build   - configure (with dynarec on x86_64) + make
#   rom     - symlink the project's pristine RISC OS 3.60 ROM dump into
#             the build's roms/ dir (exactly one file — RPCEmu
#             concatenates everything in roms/).  Override via ROM_SOURCE=
#   launch  - write a launcher script that picks the right binary
#
# Usage:
#   ./setup-rpcemu.sh                  # run all stages in order
#   ./setup-rpcemu.sh deps             # only install host deps
#   ./setup-rpcemu.sh sync             # only rsync source into build dir
#   ./setup-rpcemu.sh build            # only build (and sync first)
#   ./setup-rpcemu.sh rom              # only symlink ROM
#   ./setup-rpcemu.sh launch           # only write launcher
#
# Environment variable overrides:
#   RPCEMU_ROOT          install root (default: $HOME/opt/rpcemu)
#   RPCEMU_BUILD_DIR     where to build (default: $RPCEMU_ROOT/build)
#   ROM_SOURCE           absolute path to ROM (default: <repo>/ROMS/dump/RiscOS_3.60.rom)
#   APT                  apt-get binary (default: sudo apt-get)
#
# References:
#   external/rpcemu/VENDOR.md                                 (vendor notes)
#   https://www.marutan.net/rpcemu/linuxcompile.html          (build docs)

set -euo pipefail

RPCEMU_ROOT="${RPCEMU_ROOT:-$HOME/opt/rpcemu}"
RPCEMU_BUILD_DIR="${RPCEMU_BUILD_DIR:-$RPCEMU_ROOT/build}"
APT="${APT:-sudo apt-get}"

# Resolve project root from this script's path: tools/raster-lab/scripts/ -> repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENDORED_SRC="$PROJECT_ROOT/external/rpcemu"

# Default to the pristine RISC OS 3.60 dump.  Matches the version pinned by
# the external/Kernel/ submodule (RO_3_60), so kernel source and OS behaviour
# in the emulator line up.  The project's physical-machine merged.bin has
# bit errors that prevent VIDC20 init from completing — use that explicitly
# via ROM_SOURCE=... if you want to test emulation against the hardware's
# actual ROM state (e.g. for cross-checking bit-error diagnosis).
ROM_SOURCE="${ROM_SOURCE:-$PROJECT_ROOT/ROMS/dump/RiscOS_3.60.rom}"

log()  { printf '\033[1;34m[setup-rpcemu]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[setup-rpcemu] WARNING:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[setup-rpcemu] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

stage_deps() {
  log "Installing Qt5 + build deps via $APT"
  $APT update
  $APT install -y \
    build-essential \
    qtbase5-dev \
    qtmultimedia5-dev \
    libqt5multimedia5-plugins \
    libxcb-cursor0 \
    rsync
}

stage_sync() {
  log "Syncing vendored source -> $RPCEMU_BUILD_DIR"
  [[ -d "$VENDORED_SRC/src/qt5" ]] || die "Vendored source missing at $VENDORED_SRC"
  mkdir -p "$RPCEMU_BUILD_DIR"

  # rsync preserves whatever was previously built in the destination —
  # so make picks up only what actually changed in the source.  --delete
  # cleans up files removed from the vendored tree.  Excludes ensure we
  # never overwrite build artifacts or runtime files that live in the
  # build dir.
  rsync -a --delete \
    --exclude='/rpcemu-recompiler' \
    --exclude='/rpcemu-interpreter' \
    --exclude='/src/qt5/release/' \
    --exclude='/src/qt5/Makefile' \
    --exclude='/src/qt5/.qmake.stash' \
    --exclude='/roms/ROM' \
    --exclude='/roms/RO*' \
    --exclude='/rpc.cfg' \
    --exclude='/rpclog.txt' \
    --exclude='/cmos.ram' \
    --exclude='/hd4.hdf' \
    --exclude='/build-cross-output.txt' \
    "$VENDORED_SRC/" "$RPCEMU_BUILD_DIR/"

  log "  Sync complete ($(find "$RPCEMU_BUILD_DIR" -type f | wc -l) files)"
}

stage_build() {
  log "Building RPCEmu"

  # Always sync first so that any commits to external/rpcemu/ propagate.
  stage_sync

  # Short-circuit only if both source-side and binary-side timestamps
  # suggest the build is current (rsync would have touched files).
  if [[ -x "$RPCEMU_BUILD_DIR/rpcemu-recompiler" ]] || \
     [[ -x "$RPCEMU_BUILD_DIR/rpcemu-interpreter" ]]; then
    # Check if any source file is newer than the binary
    local binary
    if [[ -x "$RPCEMU_BUILD_DIR/rpcemu-recompiler" ]]; then
      binary="$RPCEMU_BUILD_DIR/rpcemu-recompiler"
    else
      binary="$RPCEMU_BUILD_DIR/rpcemu-interpreter"
    fi
    if [[ -z "$(find "$RPCEMU_BUILD_DIR/src" -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' \) -newer "$binary" -print -quit)" ]]; then
      log "  rpcemu binary already up to date; skipping build"
      return 0
    fi
    log "  Source newer than binary; rebuilding"
  fi

  cd "$RPCEMU_BUILD_DIR/src/qt5"

  # Enable dynamic recompiler on x86/x86_64 hosts.  rpcemu.pro defaults to
  # interpreter-only; one line edit flips it on.  dynarec is x86-only per
  # upstream docs.
  local arch
  arch=$(uname -m)
  case "$arch" in
    x86_64|i686|i386)
      log "  Host arch $arch supports dynarec; enabling in rpcemu.pro"
      if ! grep -q 'debug_and_release dynarec' rpcemu.pro; then
        sed -i 's/^CONFIG += debug_and_release$/CONFIG += debug_and_release dynarec/' rpcemu.pro
      fi
      ;;
    *)
      log "  Host arch $arch is not x86; building interpreter only"
      ;;
  esac

  log "  Running buildit.sh"
  ./buildit.sh

  log "  Running make ($(nproc) jobs)"
  make -j"$(nproc)"

  # With dynarec the build produces rpcemu-recompiler; without it,
  # rpcemu-interpreter.
  local found=0
  if [[ -x "$RPCEMU_BUILD_DIR/rpcemu-recompiler" ]]; then
    log "  Built: $RPCEMU_BUILD_DIR/rpcemu-recompiler (dynarec)"
    found=1
  fi
  if [[ -x "$RPCEMU_BUILD_DIR/rpcemu-interpreter" ]]; then
    log "  Built: $RPCEMU_BUILD_DIR/rpcemu-interpreter"
    found=1
  fi
  [[ "$found" == "1" ]] || die "Build completed but no rpcemu-{recompiler,interpreter} binary found"
}

stage_rom() {
  log "Linking ROM into emulator's roms/ directory"
  [[ -f "$ROM_SOURCE" ]] || die "ROM source not found: $ROM_SOURCE"
  local roms_dir="$RPCEMU_BUILD_DIR/roms"
  mkdir -p "$roms_dir"
  local dest="$roms_dir/ROM"

  # RPCEmu's roms.txt: "all files that don't start with '.' or have
  # extension 'txt' will be joined together in alphabetical order".
  # So we MUST keep exactly one ROM file here — any second file gets
  # concatenated and the resulting blob isn't a valid RISC OS ROM.
  find "$roms_dir" -maxdepth 1 -type l ! -name 'ROM' -delete 2>/dev/null || true

  if [[ -L "$dest" ]] && [[ "$(readlink -f "$dest")" == "$(readlink -f "$ROM_SOURCE")" ]]; then
    log "  $dest already points at $ROM_SOURCE"
  else
    rm -f "$dest"
    ln -s "$ROM_SOURCE" "$dest"
    log "  $dest -> $ROM_SOURCE"
  fi

  echo
  echo "  ROM size:       $(stat -c%s "$ROM_SOURCE") bytes"
  echo "  ROM sha256:     $(sha256sum "$ROM_SOURCE" | awk '{print $1}')"
}

stage_launch() {
  local launcher="$RPCEMU_ROOT/rpcemu.sh"
  log "Writing launcher to $launcher"

  cat > "$launcher" <<EOF
#!/usr/bin/env bash
# Launch RPCEmu from its build dir so it finds roms/ and writes its
# config alongside the binary.  Picks recompiler if available, falls
# back to interpreter.
#
# Default to xcb / XWayland: native Wayland blocks programmatic cursor
# positioning (security model), which RPCEmu needs for mouse-grab modes.
# Override to wayland-native if you don't need mouse grab:
#   QT_QPA_PLATFORM=wayland $launcher
set -e
export QT_QPA_PLATFORM="\${QT_QPA_PLATFORM:-xcb}"
cd "$RPCEMU_BUILD_DIR"
if [[ -x ./rpcemu-recompiler ]]; then
  exec ./rpcemu-recompiler "\$@"
else
  exec ./rpcemu-interpreter "\$@"
fi
EOF
  chmod +x "$launcher"

  log "  Launcher: $launcher"
  log "  Run with: $launcher"
}

print_first_run_hints() {
  cat <<EOF

  ─────────────────────────────────────────────────────────────────
  First run: RPCEmu will open a configuration dialog. Suggested
  settings for parity with the user's physical RISC PC:

    Machine:        Risc PC
    CPU:            StrongARM (SA-110) — or ARM710 for comparison
    RAM:            64 MB
    VRAM:           2 MB  (authentic; bump to 8 MB for Phase 5 stretch)
    ROM:            $RPCEMU_BUILD_DIR/roms/ROM
                    (symlink to $ROM_SOURCE)

  Once the desktop boots, mount this repo via HostFS:
    Configure -> HostFS -> set path to:
      $PROJECT_ROOT

  RPCEmu writes rpc.cfg / rpclog.txt / cmos.ram in $RPCEMU_BUILD_DIR.

  Launch:
    $RPCEMU_ROOT/rpcemu.sh
  ─────────────────────────────────────────────────────────────────
EOF
}

main() {
  local stages=(deps sync build rom launch)

  case "${1:-}" in
    deps|sync|build|rom|launch)
      stages=("$1")
      ;;
    -h|--help)
      sed -n '2,40p' "$0"
      exit 0
      ;;
    "")
      ;;
    *)
      die "Unknown argument: $1 (try --help)"
      ;;
  esac

  for stage in "${stages[@]}"; do
    "stage_$stage"
  done

  if [[ "${stages[*]}" == *"launch"* ]]; then
    print_first_run_hints
  fi

  log "Done."
}

main "$@"
