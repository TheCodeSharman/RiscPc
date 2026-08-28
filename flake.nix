{
  description = "RISC PC repair & diagnostics — dev shell for docs, decoders, and bench tests";

  inputs = {
    # Pinned to match ~/Projects/nix-config (nixos-26.05).
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" ];
      forAllSystems = f:
        nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs:
        let
          # Bench-test scripts (repair/riscpc-rtc-repair/) drive a serial bridge;
          # schemdraw renders the reverse-engineered sound schematic
          # (repair/riscpc-sound-repair/schematic/).
          pythonEnv = pkgs.python3.withPackages (ps: [
            ps.pyserial
            ps.schemdraw
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.poppler-utils   # pdftoppm — render schematics/datasheets to PNG
              pkgs.librsvg         # rsvg-convert — rasterise generated .svg schematics
              pythonEnv            # python3 + pyserial (RTC bench) + schemdraw (schematics)
            ];

            # DSView (system-wide, from the TheCodeSharman/DSView fork) loads
            # decoders from every search path and stacks them, so this just adds
            # the POST decoders on top of the bundled set. See CLAUDE.md.
            shellHook = ''
              export SIGROKDECODE_DIR="$PWD/acorn-post/decoders"
              echo "RiscPc dev shell — pdftoppm, python3+pyserial+schemdraw; SIGROKDECODE_DIR set."
            '';
          };

          # Code-CAD for the printed parts in mechanical/. Separate from
          # `default` because none of it comes from nixpkgs: build123d rests on
          # cadquery-ocp, an OpenCascade binding published only as prebuilt
          # wheels, so the environment is a uv venv pinned by mechanical/uv.lock
          # rather than a nix closure. uv fetches its own CPython too -- on
          # NixOS that interpreter and the wheels' bundled shared objects run
          # under nix-ld (see nix-config modules/nixos/nix-ld.nix).
          cad = pkgs.mkShell {
            packages = [
              pkgs.uv
              pkgs.librsvg       # rsvg-convert — rasterise exported .svg views
            ];
            shellHook = ''
              echo "RiscPc cad shell — uv $(uv --version | cut -d' ' -f2)."
              echo "  cd mechanical && uv sync   # then select .venv in VS Code"
            '';
          };

          # Kept separate from `default` so the everyday shell stays lean: this
          # is only for the tscircuit evaluation in
          # repair/riscpc-sound-repair/schematic/tscircuit/, which pulls its
          # own deps from npm rather than nixpkgs.
          tscircuit = pkgs.mkShell {
            packages = [
              pkgs.nodejs
              pkgs.bun           # the tscircuit CLI shells out to bun
              pkgs.librsvg       # rsvg-convert — rasterise the exported .svg
            ];
            shellHook = ''
              echo "RiscPc tscircuit shell — node $(node -v), npm $(npm -v), bun $(bun -v)."
            '';
          };
        });
    };
}
