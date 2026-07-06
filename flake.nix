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
          # ymodem isn't in nixpkgs; pin upstream inline. Used by
          # tools/gbsc-pro-flasher to flash the GBSC Pro AV module over YMODEM.
          ymodem = pkgs.python3Packages.buildPythonPackage {
            pname = "ymodem";
            version = "1.5";
            pyproject = true;
            src = pkgs.fetchFromGitHub {
              owner = "alexwoo1900";
              repo = "ymodem";
              rev = "1d9611bb5d1b4c01149b228aeee9893588d424ef";
              hash = "sha256-UeGF/qbEIwnHpXfouCXwAv19pNOqXJlmqNfsdK7Iz90=";
            };
            build-system = [ pkgs.python3Packages.setuptools ];
            dependencies = with pkgs.python3Packages; [ ordered-set pyserial ];
          };
          # Bench-test scripts (repair/riscpc-rtc-repair/) drive a serial bridge;
          # gbsc-pro-flasher needs ymodem.
          pythonEnv = pkgs.python3.withPackages (ps: [ ps.pyserial ymodem ]);
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
