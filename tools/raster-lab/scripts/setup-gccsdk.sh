#!/usr/bin/env bash
# setup-gccsdk.sh
#
# Repeatable GCCSDK install for cross-compiling RISC OS binaries from a Linux host.
# Tested target: Pop!_OS / Ubuntu derivatives. Other Debian-family systems should work.
#
# Stages (each is idempotent; safe to re-run):
#   deps    - install host build dependencies via apt
#   source  - checkout GCCSDK autobuilder + gcc4 from canonical SVN repo
#   build   - pre-stage dead-URL tarballs (PPL, newlib, cloog-ppl) then run
#             gcc4/build-world (SLOW - hours; backgroundable)
#   activate - write $GCCSDK_ROOT/activate.sh to source into your shell
#
# Usage:
#   ./setup-gccsdk.sh                  # run all stages in order
#   ./setup-gccsdk.sh deps             # only install host deps
#   ./setup-gccsdk.sh source           # only checkout sources
#   ./setup-gccsdk.sh build            # only run gcc4/build-world
#   ./setup-gccsdk.sh activate         # only write activation script
#   ./setup-gccsdk.sh --skip-build     # everything except the multi-hour build
#
# Environment variable overrides:
#   GCCSDK_ROOT              install root (default: $HOME/opt/gccsdk)
#   GCCSDK_SVN_BASE          canonical source URL (default: svn://svn.riscos.info/gccsdk/trunk)
#   APT                      apt-get binary (default: sudo apt-get)
#
# References:
#   https://www.stevefryatt.org.uk/risc-os/build-tools/environment
#   https://www.riscos.info/index.php/Using_GCCSDK
#   https://github.com/jhamby/riscos-gccsdk   (GitHub mirror, fallback)

set -euo pipefail

GCCSDK_ROOT="${GCCSDK_ROOT:-$HOME/opt/gccsdk}"
GCCSDK_SVN_BASE="${GCCSDK_SVN_BASE:-svn://svn.riscos.info/gccsdk/trunk}"
APT="${APT:-sudo apt-get}"

export GCCSDK_INSTALL_CROSSBIN="$GCCSDK_ROOT/cross/bin"
export GCCSDK_INSTALL_ENV="$GCCSDK_ROOT/env"

log()  { printf '\033[1;34m[setup-gccsdk]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[setup-gccsdk] WARNING:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[setup-gccsdk] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

stage_deps() {
  log "Installing host build dependencies via $APT"
  # Per stevefryatt.org.uk environment guide + GCCSDK wiki.
  # apt-get install is a no-op for already-installed packages, so re-running is cheap.
  $APT update
  $APT install -y \
    subversion git \
    build-essential gcc g++ make \
    autoconf automake automake1.11 libtool autogen \
    bison flex gperf m4 patch sed \
    texinfo help2man pkg-config \
    libtool-bin \
    wget unzip \
    libglib2.0-dev libpopt-dev \
    gettext intltool \
    meson \
    doxygen \
    dpkg-dev

  # Texinfo gotcha: modern Ubuntu (24.04+) ships texinfo 7.x which has been
  # reported to break parts of the GCC 10/12 build the autobuilder pulls in.
  # See the stevefryatt page for the documented workaround (downgrade to 6.7).
  local ti_ver
  ti_ver=$(makeinfo --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "0.0")
  local ti_major="${ti_ver%%.*}"
  if [[ "${ti_major:-0}" -ge 7 ]]; then
    warn "texinfo $ti_ver detected. Recent versions can break the GCC build."
    warn "If 'build' stage fails inside texinfo/info, downgrade to texinfo 6.7."
    warn "See: https://www.stevefryatt.org.uk/risc-os/build-tools/environment"
  fi
}

stage_source() {
  log "Checking out GCCSDK sources to $GCCSDK_ROOT"
  mkdir -p "$GCCSDK_ROOT"
  cd "$GCCSDK_ROOT"

  if [[ -d autobuilder/.svn ]]; then
    log "autobuilder/ already checked out; running svn update"
    ( cd autobuilder && svn update )
  else
    log "svn co $GCCSDK_SVN_BASE/autobuilder/"
    svn co "$GCCSDK_SVN_BASE/autobuilder/" autobuilder
  fi

  if [[ -d gcc4/.svn ]]; then
    log "gcc4/ already checked out; running svn update"
    ( cd gcc4 && svn update )
  else
    log "svn co $GCCSDK_SVN_BASE/gcc4/"
    svn co "$GCCSDK_SVN_BASE/gcc4/" gcc4
  fi
}

# Pre-fetch helpers.  GCCSDK's Makefile invokes wget against pre-baked upstream
# URLs; several have bit-rotted (bugseng.com 301s to homepage, sources.redhat.com
# FTP is gone, etc).  Make only triggers wget if the target file is absent, so
# pre-staging a valid copy under srcdir.orig/ side-steps the dead URLs.
prefetch_url() {
  local dest="$1" url="$2" min_size="${3:-1000000}"
  if [[ -f "$dest" ]] && [[ $(stat -c%s "$dest") -ge "$min_size" ]]; then
    log "  $(basename "$dest") already staged ($(stat -c%s "$dest") bytes); skipping"
    return 0
  fi
  rm -f "$dest"
  log "  Fetching $url"
  curl -sLfo "$dest" "$url" || die "Download failed: $url"
  touch "$dest"
}

prefetch_repack_xz_to_gz() {
  local dest="$1" url="$2" expected_sha512="${3:-}"
  if [[ -f "$dest" ]] && [[ $(stat -c%s "$dest") -gt 1000000 ]]; then
    log "  $(basename "$dest") already staged ($(stat -c%s "$dest") bytes); skipping"
    return 0
  fi
  rm -f "$dest"
  local tmp_xz="${dest%.tar.gz}.orig.tar.xz"
  log "  Fetching $url"
  curl -sLfo "$tmp_xz" "$url" || die "Download failed: $url"
  if [[ -n "$expected_sha512" ]]; then
    local actual; actual=$(sha512sum "$tmp_xz" | awk '{print $1}')
    if [[ "$actual" != "$expected_sha512" ]]; then
      rm -f "$tmp_xz"
      die "SHA512 mismatch on $(basename "$tmp_xz")"
    fi
    log "  SHA512 verified"
  fi
  log "  Repacking xz -> gz as $(basename "$dest")"
  xz -dc "$tmp_xz" | gzip -c > "$dest"
  touch "$dest"
}

stage_prefetch() {
  log "Pre-staging upstream tarballs with dead/moved URLs"
  local srcorig="$GCCSDK_ROOT/gcc4/srcdir.orig"
  [[ -d "$GCCSDK_ROOT/gcc4" ]] || die "gcc4/ not present - run 'source' stage first"
  mkdir -p "$srcorig"

  # PPL 1.2: bugseng.com URL 301s to homepage.  Pop!_OS apt mirror has the
  # Debian-orig as .tar.xz; repack to .tar.gz under the expected filename.
  prefetch_repack_xz_to_gz "$srcorig/ppl-1.2.tar.gz" \
    "http://apt.pop-os.org/ubuntu/pool/universe/p/ppl/ppl_1.2.orig.tar.xz" \
    "b509ed85fa6aedd40119bd4c980b17f33072c56c2acd923da3445b6bc80d48051cfa4c04cce96f6974711f5279c24b31cb3869f87b2eb6a2a1b30a058c809350"

  # newlib 1.19.0: sources.redhat.com FTP is gone.  sourceware.org https works.
  prefetch_url "$srcorig/newlib-1.19.0.tar.gz" \
    "https://sourceware.org/pub/newlib/newlib-1.19.0.tar.gz"

  # cloog-ppl 0.15.11: FTP works inconsistently; pre-stage from gcc.gnu.org https.
  prefetch_url "$srcorig/cloog-ppl-0.15.11.tar.gz" \
    "https://gcc.gnu.org/pub/gcc/infrastructure/cloog-ppl-0.15.11.tar.gz" \
    500000
}

stage_build() {
  log "Running build-world - this is SLOW (multiple hours). Output streams below."
  log "Install paths:"
  log "  GCCSDK_INSTALL_CROSSBIN=$GCCSDK_INSTALL_CROSSBIN"
  log "  GCCSDK_INSTALL_ENV=$GCCSDK_INSTALL_ENV"
  local gcc4_dir="$GCCSDK_ROOT/gcc4"
  [[ -d "$gcc4_dir" ]] || die "gcc4/ not present - run 'source' stage first"

  # Skip if the cross-compiler binary already exists. Lets re-runs short-circuit.
  if compgen -G "$GCCSDK_INSTALL_CROSSBIN/arm-*-gcc" > /dev/null; then
    log "Cross-compiler appears installed at $GCCSDK_INSTALL_CROSSBIN; skipping build."
    log "Force a rebuild by removing that directory."
    return 0
  fi

  # Pre-populate gccsdk-params so build-world doesn't do the first-run
  # "please review the file" exit dance.  The file lives in gcc4/ and is
  # sourced by setup-gccsdk-params at the start of every build-world run.
  local params="$gcc4_dir/gccsdk-params"
  if [[ ! -f "$params" ]]; then
    log "Pre-populating $params"
    cat > "$params" <<EOF
# Generated by setup-gccsdk.sh
# Install location for the cross-compiler binaries (path must end in 'bin')
export GCCSDK_INSTALL_CROSSBIN=$GCCSDK_INSTALL_CROSSBIN
# Install location for the porting tools and built RISC OS libraries
export GCCSDK_INSTALL_ENV=$GCCSDK_INSTALL_ENV
EOF
  fi

  # Stage any tarballs whose Makefile-baked URLs have died.
  stage_prefetch

  # texinfo 7.x rejects syntax in GCC 4.7.4's .texi files (sourcebuild.texi
  # line 679: `@itemx should not begin @table`).  GCCSDK's recursive make
  # hardcodes `MAKEINFO=makeinfo ...` as a command-line argument to
  # sub-makes, defeating both env-level overrides and the BUILD_INFO knob.
  # Cleanest workaround: PATH-shim a stub makeinfo that touches the output
  # file and exits 0, making info-doc generation a silent no-op.  Steve
  # Fryatt's documented alternative was downgrading texinfo to 6.7 — more
  # invasive and affects everything else on the system.
  local shimdir="$GCCSDK_ROOT/shims"
  mkdir -p "$shimdir"
  cat > "$shimdir/makeinfo" <<'SHIM_EOF'
#!/bin/sh
# Stub makeinfo - bypasses texinfo 7 incompatibility with GCC 4.7.4 docs.
# Parses -o to find the output file, creates an empty one, exits success.
while [ $# -gt 0 ]; do
  case "$1" in
    -o) shift; [ -n "$1" ] && { mkdir -p "$(dirname -- "$1")" 2>/dev/null; : > "$1"; } ;;
  esac
  shift
done
exit 0
SHIM_EOF
  chmod +x "$shimdir/makeinfo"

  # Namespace clash: our GCCSDK_ROOT is the install prefix; their
  # setup-gccsdk-params uses GCCSDK_ROOT to mean the gcc4/ source dir
  # and auto-detects from the script's dirname if unset.  Unset in the
  # child env so their auto-detect kicks in correctly.  Prepend shimdir
  # so the stub makeinfo wins over /usr/bin/makeinfo.
  ( cd "$gcc4_dir" && unset GCCSDK_ROOT && PATH="$shimdir:$PATH" ./build-world )
}

stage_activate() {
  local activate="$GCCSDK_ROOT/activate.sh"
  log "Writing activation script to $activate"
  mkdir -p "$GCCSDK_ROOT"
  cat > "$activate" <<EOF
# Source this to put the GCCSDK cross-toolchain on PATH.
export GCCSDK_INSTALL_CROSSBIN="$GCCSDK_INSTALL_CROSSBIN"
export GCCSDK_INSTALL_ENV="$GCCSDK_INSTALL_ENV"
case ":\$PATH:" in
  *":\$GCCSDK_INSTALL_CROSSBIN:"*) ;;
  *) export PATH="\$GCCSDK_INSTALL_CROSSBIN:\$PATH" ;;
esac
EOF
  log "To activate in your current shell: source $activate"
}

verify_install() {
  log "Verifying install..."
  if compgen -G "$GCCSDK_INSTALL_CROSSBIN/arm-*-gcc" > /dev/null; then
    local gcc_bin
    gcc_bin=$(compgen -G "$GCCSDK_INSTALL_CROSSBIN/arm-*-gcc" | head -1)
    log "Found cross-compiler: $gcc_bin"
    "$gcc_bin" --version | head -1 || true
  else
    warn "No cross-compiler binary found under $GCCSDK_INSTALL_CROSSBIN"
    warn "Build may have failed or been skipped."
  fi
}

main() {
  local skip_build=0
  local stages=(deps source build activate)

  case "${1:-}" in
    deps|source|build|activate)
      stages=("$1")
      ;;
    --skip-build)
      skip_build=1
      ;;
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    "")
      ;;
    *)
      die "Unknown argument: $1 (try --help)"
      ;;
  esac

  for stage in "${stages[@]}"; do
    if [[ "$stage" == "build" && "$skip_build" == "1" ]]; then
      log "Skipping build stage (--skip-build)"
      continue
    fi
    "stage_$stage"
  done

  if [[ "${stages[*]}" == *"build"* && "$skip_build" != "1" ]]; then
    verify_install
  fi

  log "Done."
}

main "$@"
