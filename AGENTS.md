# Public repository instructions

- This is a deliberately partial public research release. Read LEGAL.md first.
- Never import a private repository, its Git history, LFS objects, generated game code, game data or real diagnostic fixtures.
- Do not add credentials, licensing/key-generation code, signing material, device identifiers or private paths.
- Publish reviewed original methods, source and tooling as broadly as practical. Tools may process user-supplied local game inputs; never publish those inputs or generated game code. Do not add protection-bypass instructions.
- Preserve the MIT license and provenance. Third-party code needs its own reviewed attribution and licensing; see THIRD_PARTY.md and LICENSES for the included patch contexts.
- Every public file must be in PUBLICATION.json. An inventory edit is not permission to publish unreviewed content.
- Run `python -B tools/verify.py` before publication, inspect staged changes, and rerun after committing to check new history.
- Tests use only synthetic inputs and temporary directories outside the checkout.
- Exception authorized by the maintainer: up to six individually reviewed video stills under docs/images/, documented in docs/SCREENSHOTS.md and pinned by SHA-256 in PUBLICATION.json. Game imagery is not MIT-licensed. Do not add arbitrary images or real game test fixtures.
- State the difference between development observations and tests reproducible from this public repository. Do not claim complete ports, full API coverage or full-match multiplayer stability without matching evidence.
