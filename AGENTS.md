# Public repository instructions

- This is a deliberately partial public research release. Read LEGAL.md first.
- Never import a private repository, its Git history, LFS objects, generated game code, game data or real diagnostic fixtures.
- Do not add credentials, licensing/key-generation code, signing material, device identifiers or private paths.
- Keep descriptions at the architectural level. Do not reconstruct missing private tooling or add protection-bypass instructions.
- Preserve the MIT license and provenance. Third-party code needs its own reviewed attribution and licensing; the current release vendors none.
- Every public file must be in PUBLICATION.json. An inventory edit is not permission to publish unreviewed content.
- Run `python -B tools/verify.py` before publication, inspect staged changes, and rerun after committing to check new history.
- Tests use only synthetic inputs and temporary directories outside the checkout.
- State the difference between development observations and tests reproducible from this public repository. Do not claim complete ports, full API coverage or verified multiplayer.
