# RISC OS BASIC readable-diff filter

Tokenised BBC BASIC (`,ffb`) is binary, so plain `git diff` shows nothing
useful. This wires up a git **textconv** filter that detokenises `,ffb` files to
text *for diff display only* — the committed bytes stay the real tokenised,
buildable module (RISC OS can still load/run them, hostfs keeps the type).

Detokeniser: **`bastotxt`** from
[gerph/riscos-basic-detokenise](https://github.com/gerph/riscos-basic-detokenise)
(Justin Fletcher, **MIT**). Verified on `rafs/rafs116src/raFSsource,ffb` —
decodes BASIC V correctly, inline `[ OPT ]` assembler and all.

## Enable (once per clone)

```sh
./setup.sh          # clones + builds ./bastotxt   (needs gcc + make)
git config diff.riscosbasic.textconv \
    tools/riscos-basic-detokenise/bastotxt-textconv.sh
```

On NixOS: `nix-shell -p gcc gnumake --run ./setup.sh`.

Then `git diff`/`git show` on any `*,ffb` file renders detokenised BASIC.

## How it hangs together

- **`.gitattributes`** (repo root, committed): `*,ffb diff=riscosbasic` maps the
  tokenised files to the `riscosbasic` diff driver.
- **git config** (local, from the setup step): points that driver's `textconv`
  at `bastotxt-textconv.sh`. Not shared by clone — hence `setup.sh`.
- **`bastotxt-textconv.sh`** (committed): tiny wrapper, `bastotxt -i <path>`.
- **`bastotxt`** + **`.build/`** (gitignored): the binary and its build clone;
  rebuild anytime with `setup.sh`.

Without the local config a fresh clone just treats `,ffb` as binary — safe
fallback, no breakage.
