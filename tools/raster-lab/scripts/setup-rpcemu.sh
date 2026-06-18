#!/usr/bin/env bash
# setup-rpcemu.sh
#
# Repeatable RPCEmu install on Linux hosts.  Clones the project's RPCEmu
# fork (TheCodeSharman/rpcemu), checks out the branch with our patches
# applied, enables the dynamic recompiler on x86_64 hosts, and symlinks
# a pristine RISC OS ROM into the emulator's roms/ directory.
#
# The fork is based on v0.9.5 mainline plus:
#   - philpem's os_reset patch (SWI poweroff support, cherry-picked)
#   - VRAM-honesty patch (Configure / settings / romload — exposes real
#     None / 1 / 2 / 8 MB options instead of mainline's hard-coded 0 or 8)
#
# Tested target: Pop!_OS 24.04 / Ubuntu derivatives.
#
# Stages (each is idempotent; safe to re-run):
#   deps    - install Qt5 + build deps via apt
#   source  - git clone the project's RPCEmu fork on the configured branch
#   build   - run buildit.sh + make; enables dynarec on x86_64
#   rom     - symlink the project's pristine RISC OS 3.60 ROM dump into
#             the emulator's roms/ dir (exactly one file — RPCEmu
#             concatenates everything in roms/).  Override via ROM_SOURCE=
#   launch  - write a launcher script that puts everything on PATH
#
# Usage:
#   ./setup-rpcemu.sh                  # run all stages in order
#   ./setup-rpcemu.sh deps             # only install host deps
#   ./setup-rpcemu.sh source           # only clone the fork
#   ./setup-rpcemu.sh build            # only build
#   ./setup-rpcemu.sh rom              # only symlink ROM
#   ./setup-rpcemu.sh launch           # only write launcher
#
# Environment variable overrides:
#   RPCEMU_FORK_URL      git URL to clone (default: TheCodeSharman/rpcemu)
#   RPCEMU_FORK_BRANCH   branch to check out (default: feature/vram-honesty)
#   RPCEMU_ROOT          install root (default: $HOME/opt/rpcemu)
#   ROM_SOURCE           absolute path to ROM (default: <repo>/ROMS/dump/RiscOS_3.60.rom)
#   APT                  apt-get binary (default: sudo apt-get)
#
# References:
#   https://github.com/TheCodeSharman/rpcemu                  (our fork)
#   https://github.com/philpem/rpcemu                         (upstream-of-fork)
#   https://www.marutan.net/rpcemu/                           (mainline)
#   https://www.marutan.net/rpcemu/linuxcompile.html          (build docs)

set -euo pipefail

RPCEMU_FORK_URL="${RPCEMU_FORK_URL:-https://github.com/TheCodeSharman/rpcemu.git}"
# main is the fork's integration branch (upstream + all patches applied).
# upstream is RPCEmu mainline pristine, individual patches live on
# feature/* branches with standing PRs.
RPCEMU_FORK_BRANCH="${RPCEMU_FORK_BRANCH:-main}"
RPCEMU_ROOT="${RPCEMU_ROOT:-$HOME/opt/rpcemu}"
APT="${APT:-sudo apt-get}"

# Resolve project root from this script's path: tools/raster-lab/scripts/ -> repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# Default to the pristine RISC OS 3.60 dump.  Matches the version pinned by
# the external/Kernel/ submodule (RO_3_60), so kernel source and OS behaviour
# in the emulator line up.  The project's physical-machine merged.bin has
# bit errors that prevent VIDC20 init from completing — use that explicitly
# via ROM_SOURCE=... if you want to test emulation against the hardware's
# actual ROM state (e.g. for cross-checking bit-error diagnosis).
ROM_SOURCE="${ROM_SOURCE:-$PROJECT_ROOT/ROMS/dump/RiscOS_3.60.rom}"

RPCEMU_SRC_DIR="$RPCEMU_ROOT/rpcemu"

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
    git \
    wget
}

stage_source() {
  log "Cloning project RPCEmu fork from $RPCEMU_FORK_URL ($RPCEMU_FORK_BRANCH)"
  mkdir -p "$RPCEMU_ROOT"

  if [[ -d "$RPCEMU_SRC_DIR/.git" ]]; then
    log "  Repo already cloned at $RPCEMU_SRC_DIR; fetching + checking out branch"
    ( cd "$RPCEMU_SRC_DIR" \
        && git fetch --tags origin \
        && git checkout "$RPCEMU_FORK_BRANCH" \
        && git pull --ff-only origin "$RPCEMU_FORK_BRANCH" 2>/dev/null || true )
  else
    git clone --branch "$RPCEMU_FORK_BRANCH" "$RPCEMU_FORK_URL" "$RPCEMU_SRC_DIR"
  fi

  [[ -d "$RPCEMU_SRC_DIR/src/qt5" ]] || die "Expected RPCEmu source layout missing under $RPCEMU_SRC_DIR"
  log "  Checked out: $(cd "$RPCEMU_SRC_DIR" && git log --oneline -1)"
}

stage_build() {
  log "Building RPCEmu"
  [[ -d "$RPCEMU_SRC_DIR/src/qt5" ]] || die "src/qt5 not found - run 'source' stage first"

  # Short-circuit if either binary already exists.  With dynarec enabled the
  # build produces rpcemu-recompiler only (not rpcemu-interpreter), so accept
  # either as proof the build is done.
  if [[ -x "$RPCEMU_SRC_DIR/rpcemu-recompiler" ]] || \
     [[ -x "$RPCEMU_SRC_DIR/rpcemu-interpreter" ]]; then
    log "  rpcemu binary already built; skipping (delete it to force rebuild)"
    return 0
  fi

  cd "$RPCEMU_SRC_DIR/src/qt5"

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
      grep '^CONFIG' rpcemu.pro
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
  # rpcemu-interpreter.  Both can exist if rpcemu.pro is configured for both.
  local found=0
  if [[ -x "$RPCEMU_SRC_DIR/rpcemu-recompiler" ]]; then
    log "  Built: $RPCEMU_SRC_DIR/rpcemu-recompiler (dynarec)"
    found=1
  fi
  if [[ -x "$RPCEMU_SRC_DIR/rpcemu-interpreter" ]]; then
    log "  Built: $RPCEMU_SRC_DIR/rpcemu-interpreter"
    found=1
  fi
  [[ "$found" == "1" ]] || die "Build completed but no rpcemu-{recompiler,interpreter} binary found"
}

stage_rom() {
  log "Linking ROM into emulator's roms/ directory"
  [[ -f "$ROM_SOURCE" ]] || die "ROM source not found: $ROM_SOURCE"
  local roms_dir="$RPCEMU_SRC_DIR/roms"
  mkdir -p "$roms_dir"
  local dest="$roms_dir/ROM"

  # RPCEmu's roms.txt: "all files that don't start with '.' or have
  # extension 'txt' will be joined together in alphabetical order".
  # So we MUST keep exactly one ROM file here — any second file gets
  # concatenated and the resulting blob isn't a valid RISC OS ROM.
  # Remove any stray non-ROM files that might've been left behind.
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
# Launch RPCEmu from its install dir so it finds roms/ and writes its
# config alongside the binary.  Picks recompiler if available, falls
# back to interpreter.
#
# Default to xcb / XWayland: native Wayland blocks programmatic cursor
# positioning (security model), which RPCEmu needs for mouse-grab modes.
# XWayland inherits X11's cursor-warp semantics so the emulator's mouse
# handling works.  Override to wayland-native if you don't need mouse
# grab: QT_QPA_PLATFORM=wayland $launcher
set -e
export QT_QPA_PLATFORM="\${QT_QPA_PLATFORM:-xcb}"
cd "$RPCEMU_SRC_DIR"
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
    CPU:            StrongARM (SA-110)
                    (switch to ARM710 later for cross-core comparison;
                     same binary, different timing — that's the point)
    RAM:            64 MB
    VRAM:           2 MB
    ROM:            $RPCEMU_SRC_DIR/roms/ROM
                    (this is the symlink to $ROM_SOURCE)

  Once the desktop boots, mount this repo via HostFS:
    Configure -> HostFS -> set path to:
      $PROJECT_ROOT

  RPCEmu writes its config to $RPCEMU_SRC_DIR/rpc.cfg after first run.

  Launch:
    $RPCEMU_ROOT/rpcemu.sh
  ─────────────────────────────────────────────────────────────────
EOF
}

main() {
  local stages=(deps source build rom launch)

  case "${1:-}" in
    deps|source|build|rom|launch)
      stages=("$1")
      ;;
    -h|--help)
      sed -n '2,35p' "$0"
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
