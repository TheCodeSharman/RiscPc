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
          # Bench-test scripts (repair/riscpc-rtc-repair/) drive a serial bridge.
          pythonEnv = pkgs.python3.withPackages (ps: [ ps.pyserial ]);
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.poppler-utils   # pdftoppm — render schematics/datasheets to PNG
              pythonEnv            # python3 + pyserial for the RTC bench tests
            ];

            # DSView (system-wide, from the TheCodeSharman/DSView fork) loads
            # decoders from every search path and stacks them, so this just adds
            # the POST decoders on top of the bundled set. See CLAUDE.md.
            shellHook = ''
              export SIGROKDECODE_DIR="$PWD/acorn-post/decoders"
              echo "RiscPc dev shell — pdftoppm, python3+pyserial; SIGROKDECODE_DIR set."
            '';
          };
        });
    };
}
