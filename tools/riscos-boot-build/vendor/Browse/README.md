# Browse — Acorn's web browser stack (period-correct for RISC OS 3.7)

The Acorn **!Browse** browser and its optional caching backend, vendored for the
universal boot:

- **`!Browse`** → `$.Apps.!Browse` — the browser. HTML 3.2-era (no CSS/JS, and
  its `AcornSSL` predates modern TLS, so it **can't load today's HTTPS sites**).
  Good for local HTML/documentation and old-style HTTP/retro pages, not the
  modern web. Self-contained: it fetches via the `URL`/`AcornHTTP`/`AcornSSL`/
  `FTP`/`File` modules already in the merged `!System`, and needs the nested WIMP
  (`WindowManager 3.98+`) which the boot already loads as **5.15**, plus the
  Toolbox modules in `!System`.
- **`!WebServe`** → `!Boot.Resources.!WebServe` — an optional fetch-and-cache
  proxy for the browser (not an external web server).
- **`!WebCache`** → `!Boot.Resources.!WebCache` — the on-disc store `!WebServe`
  writes into. `!Browse` works fine without these two (direct fetch); they add
  caching, handy on a slow retro machine.

`!Browse` reads config from `Choices:WWW.Browse` and falls back to its own `User`
dir, so it creates its own choices — the machine's personal `WWW.Browse`
bookmarks/hotlist are deliberately **not** vendored.

## Provenance / licensing

Captured from the **RPCEmu RISC OS 3.71 starter disc** (`hostfs/Apps/!Browse`,
`hostfs/!Boot/Resources/!Web*`). This is Acorn Internet-suite software — still
copyright (Acorn → Pace → … → RISC OS Developments) and *not* under a
redistribution licence the way the other vendored sources are (HardDisc4/
PlingSystem from RISC OS Open, Zap from its author, PackMan Apache-2.0, RaFS
GPL). It's included here on the basis that it ships on a publicly-distributed
starter disc for a long-obsolete OS, as a deliberate choice for this personal
retro project. Not for onward redistribution as software in its own right.
