# AKG Retro Games — linux

PRIVATE, INCOMPLETE FOUNDATION. This repository contains the selected menu concept, an original icon, and tested update-manifest validation helpers. It has an experimental local-ROM frontend, but does not include ROMs, bundled cores, signing keys, a published update feed, release packages, verified cheats, or stage selection. The menu image is a mockup and its titles are illustrative.

Future updates are intended to use an externally hosted distribution service; no developer token may be embedded in the client. SHA-256 alone does not authenticate a catalog: a trusted signed manifest or equivalent trust mechanism is still required before shipping. Android package signing is separate from update metadata signing.

Developer attribution and disclaimer: [NOTICE.md](NOTICE.md). Platform icon assets are in `assets/platform-icons/`; application integration is not yet implemented.

The Linux menu has an **experimental** selection path for locally supplied, hash-matched ROMs and locally compiled cores (`--rom-dir` and `--cores-dir`). Nothing is bundled yet, no player release is available, and this is not a finished application. F5/F8 perform explicit manual save/load. CI headless probes do not replace actual device, sound, controller or full-playthrough testing.

## Engine foundation
The experimental engine registry is pinned to `midoali250/bitvault-engine` commit `4eb0473490357c1fc8b8d86af4e4f794632b9746` on `engine/clean-foundation`. NES and SNES use the registry's FCEUmm and Snes9x revisions. The engine registry is a build-probe foundation, not a finished cross-platform player. No ROMs are bundled.

The experimental display fits the full frame to the screen with letterboxing instead of stretching or cropping; it is upscaling, not native 4K. The current calculation assumes square pixels, not a calibrated console pixel aspect ratio.
