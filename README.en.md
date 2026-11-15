# RA3 recompilation research

[中文](README.md) · [Scope](LEGAL.md) · [Provenance](THIRD_PARTY.md)

Selected engineering notes and small, reusable tools from research into static x86-to-C recompilation across Windows, Android, macOS and iOS / iPad.

**This is a partial source release, not a playable port or a complete build system.** It contains no game executable, lifted/decompiled game code, assets, translated game shaders, game packages or licensing credentials. Supplying a legitimate game installation does not make this repository sufficient to build the game.

The public slice contains a CMake Dev/Release profile module, a generic image-difference tool, synthetic tests, a publication guard and newly written Chinese methodology documents. It has an independent Git history and no vendored third-party source.

## Development status, 2026-11-15

These are summarized development observations, not results reproducible from this public release:

| Platform | Observed | Still open |
| --- | --- | --- |
| Windows x86 | A complete 1.12 skirmish played by the developer | Broader and longer testing |
| Android ARM64 | 1.12 battlefield, unit selection, menus and intro audio | Full match, background recovery, latest shared changes on device |
| macOS Apple Silicon | Menus, battlefield, input and animated cursors | Full match, endurance and graphics coverage |
| iOS / iPad ARM64 | Interactive gameplay; one device retest after GPU lifetime fixes | Endurance, broader scenarios and performance cost |

iPad/Mac room discovery has been observed. Joining and completing a mixed-platform match have not been established. Full ARM64 x86 memory-order equivalence is also unresolved.

## Check the public tools

Python 3.10+, Git, CMake 3.16+ and Pillow are needed. No game installation is used.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -B tools/verify.py
git config core.hooksPath .githooks
```

The checks cover the public inventory, working files, Git index, reachable local history and synthetic tests. Keep input images and output artifacts outside the checkout. A local pre-commit hook checks staged content; CI runs after push/PR and cannot prevent an initial disclosure.

## Reading guide

- [Architecture](docs/ARCHITECTURE.md): guest state, compatibility boundary and hosts.
- [Method](docs/METHOD.md): staged bring-up and validation.
- [Porting notes](docs/PORTING-NOTES.md): synchronization, graphics lifetime and input.
- [Status](docs/STATUS.md): what each observation does and does not prove.
- [Publication review](docs/PUBLICATION.md): selection, exclusions and guard limits.

MIT applies to the material actually distributed here. It does not license the game or other third-party material, and adds no non-commercial restriction. This independent project is not affiliated with or endorsed by Electronic Arts. Product names belong to their respective rights holders.

The presentation was informed by [sc2-android-recomp](https://github.com/HolyCaonima/sc2-android-recomp); no source or prose was copied from it. See [third-party acknowledgements](THIRD_PARTY.md).
