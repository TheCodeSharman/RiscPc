# Acorn AASM (RISC OS) — VS Code Language Extension

Syntax highlighting for Acorn's AASM assembly dialect as used in the RISC OS Kernel, HdrSrc, and related ROOL sources.

## What it highlights

- `;` line comments
- `&FF` hex, `2_1010` based, decimal, and char literals
- ARM mnemonics with condition codes and width suffixes (LDR/STR/B/H/SB/SH, LDM/STM with IA/IB/DA/DB/FD/FA/EA/ED, etc.)
- Acorn-specific macros (Push, Pull, MOV_fiq, FAULT, ENTRY, EXIT, addr, ...)
- Directives: `GET`, `MACRO`/`MEND`, `ROUT`, `GBLA`/`GBLL`/`GBLS`, `SETA`/`SETL`/`SETS`, `EQU`, `DCB`/`DCW`/`DCD`, `ALIGN`, `ASSERT`, `AREA`, `EXPORT`/`IMPORT`, conditional `[ | ]`, `WHILE`/`WEND`, `IF`/`ELSE`/`ENDIF`
- Symbol operators: `*` (EQU shorthand), `&` (data word), `=` (data string), `#` (space counter), `^` (layout mark)
- Colon operators: `:AND:`, `:OR:`, `:SHL:`, `:SHR:`, `:MOD:`, `:LNOT:`, `:DEF:`, etc.
- Registers: r0-r15/R0-R15, pc, lr, sp, fp, ip, cpsr, spsr, f0-f7
- Local labels (`10`, `20`, ...) and refs (`%FT10`, `%BT10`, `%10`)
- Macro parameters (`$name`)

## Install

From the repo root:

```sh
./tools/vscode-aasm/install.sh
```

The script creates a symlink at `~/.vscode/extensions/local.aasm-riscos-0.1.0` pointing back at this folder, so edits to the grammar are picked up on the next VS Code reload (no rebuild step). Idempotent — safe to re-run.

For non-standard installs (Code-OSS, Flatpak, code-server, ...) pass the extensions directory explicitly:

```sh
./tools/vscode-aasm/install.sh --target ~/.var/app/com.visualstudio.code/data/vscode/extensions
```

Then reload VS Code (Ctrl-Shift-P → "Developer: Reload Window"). The workspace's `.vscode/settings.json` maps the RISC OS source directories to this language, so files in `external/Kernel/s/`, `external/Kernel/hdr/`, `external/Kernel/TestSrc/`, `external/Kernel/NewModes/`, and `external/HdrSrc/hdr/` will pick it up automatically.

## Uninstall

```sh
./tools/vscode-aasm/install.sh --uninstall
```

## Scope

This is a syntax-highlighting grammar only — no language server, no completions, no go-to-definition. Aimed at making RISC OS source readable while doing repair / reverse-engineering work, not at being a full IDE for AASM development.
