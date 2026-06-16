# Contributing to axonctl

Thanks for contributing! This guide covers the local setup, how to run the
checks, and the git workflow.

## Toolchain — everything lives in `.tooling/`

To keep your machine clean, **all** tooling (uv, the Python interpreter, the dev
virtualenv, and Android `adb`) is downloaded into a project-local `.tooling/`
directory by scripts in `scripts/`. Nothing is installed system-wide, and
`.tooling/` is git-ignored.

```bash
# One-shot: uv + uv-managed CPython + venv + adb, all under .tooling/
scripts/bootstrap.sh

# Or individually:
scripts/install-uv.sh     # -> .tooling/uv
scripts/setup-venv.sh     # -> .tooling/python, .tooling/venv  (axonctl[dev], editable)
scripts/install-adb.sh    # -> .tooling/platform-tools/adb
```

Then activate the environment:

```bash
source .tooling/venv/bin/activate
```

`adb` is resolved by axonctl in this order: `$AXONCTL_ADB`, then
`.tooling/platform-tools/adb`, then `adb` on `$PATH`.

## Quality gates

All four must be green before a branch is merged — this is part of every stage's
definition of done:

```bash
ruff check .
black --check .
mypy
pytest -q
```

## Git workflow (git-flow)

- `main` — releases only, always stable; each merge is tagged `vX.Y.Z`.
- `develop` — integration branch.
- `feature/<name>` — branched from `develop`, one per implementation stage.
- `release/<version>` — branched from `develop`, merged into `main` and back.
- `hotfix/<name>` — branched from `main`, merged into `main` and `develop`.

Stage flow: `feature/stageN-<short>` from `develop` → implement with tests,
docstrings, and green checks → merge into `develop` with `--no-ff` → delete the
feature branch.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `build:`) in the
imperative mood; keep them atomic (one logical change per commit).

## Code standards

- Full type hints everywhere; `mypy --strict` must pass.
- Google-style docstrings on all public API; the `Raises:` section must list the
  `RpcError` subclasses a method can raise.
- No bare `except:` — catch specific exceptions; protocol errors map to typed
  `RpcError` subclasses.
