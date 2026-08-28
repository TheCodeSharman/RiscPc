# Mechanical — printed parts

Code-CAD models for 3D-printed parts on the RISC PC, written in
[build123d](https://build123d.readthedocs.io/) (Python over OpenCascade). Each
model is a script; running it exports STEP/STL beside itself.

## Why a venv and not the nix dev shell

build123d rests on `cadquery-ocp`, the OpenCascade Python binding, which is
published only as prebuilt wheels — it is not in nixpkgs and packaging it would
mean carrying a large C++ build. So this directory pins its own environment in
`uv.lock` and the nix side supplies nothing but `uv` (in the repo's `cad` dev
shell, and in nix-config's `home.packages`).

uv fetches its own CPython 3.13 as well. On macOS that just works; on NixOS the
interpreter and the wheels' bundled shared objects run under `nix-ld`, which
nix-config already enables.

## Setup

```sh
nix develop .#cad      # from the repo root — provides uv
cd mechanical && uv sync
```

## Seeing the model

The **OCP CAD Viewer** VS Code extension (`bernhard-42.ocp-cad-viewer`, pinned
in nix-config) renders a shape in an editor pane: start the viewer from the
status bar, then `show(part)` from a running script pushes geometry to it.

Its version must stay equal to the `ocp-vscode` pin in `pyproject.toml` — the
extension and the Python module talk over a localhost port with a versioned
protocol, and a mismatch shows as a viewer that connects but draws nothing.

`.vscode/settings.json` points `python.defaultInterpreterPath` at
`mechanical/.venv`, so the extension finds a `show()`-capable interpreter
without one being selected by hand.

`smoke_test.py` is the end-to-end check: run it headless to prove the geometry
kernel loads, or run it with the viewer up to prove the rendering path works.
