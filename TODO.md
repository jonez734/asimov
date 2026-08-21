# TODO — asimov

## `_version.py` files: clean up orphans and standardize stamping

### Problem

`asimov/src/asimov/io/_version.py` exists with stale, mislabeled contents:

```python
__version__ = "b5de2de1e8e605ca"
__datestamp__ = "202310292133"
__tag__ = "ttyio6-202310292133"
```

The `__version__` field is actually a 16-character **githash** mislabeled as a version. The `__tag__ = "ttyio6-…"` and the `20231029` datestamp suggest this is a leftover from when `asimov.io` was forked from the older `ttyio6` package. The file is **not imported anywhere** in the asimov source tree or in any sibling project — `grep` for `asimov.io._version` and `asimov.io.__version__` returns zero hits. The `b5de2de1e8e605ca` value is the same githash that used to live in the now-deleted `bbsengine6/io/_version.py` (removed 2026-06-26 in the `bbsengine6` cleanup).

In addition, the asimov project has **no `make version` target and no per-package `_version.py` for `asimov` itself** — sibling projects (`bed`, `zoid6`, `empyre`, `bbsengine6`, `murdermotel`, `backuptools`) all have one. As a result, `asimov.__version__` is not defined at the package level, and there is no consistent way to stamp the asimov wheel with a version + githash.

### Why this matters

- The orphan `asimov.io._version.py` is a footgun: it looks like a real version file but contains a githash where a version should be. If a future contributor imports it, they'll get the wrong symbol name and a value that's nearly two years old.
- The lack of a `make version` target means asimov wheels are stamped by hand or by the build backend's auto-version (e.g. `setuptools-scm` or a fixed string), neither of which is consistent with the rest of the monorepo.

### Cleanup tasks

#### 1. Decide the fate of `asimov/src/asimov/io/_version.py`

Three options, in order of cleanliness:

- **a. Delete the file.** Cleanest. Zero importers today. Matches the cleanup just done in `bbsengine6` (where the same orphan was deleted on 2026-06-26). If something is silently depending on it, grep will catch it before the delete; if not, removing the mislabeled file is the right default.
- **b. Rename the symbols in place.** Change `__version__` → `githash` (matching `bed/src/bed/_version.py:2`, `zoid6/src/zoid6/_version.py:2`, `empyre/src/empyre/_version.py:2`). Keep `__datestamp__` and `__tag__` if they're useful. Honest but pointless if nothing imports it.
- **c. Repurpose the file as a real `io`-subpackage version.** Stamp it from a `make version` target in `asimov/src/Makefile` so the `io` subpackage has its own version. Only worth it if some downstream consumer will read `asimov.io.__version__`.

**Recommendation: (a) delete.** The same file was deleted from `bbsengine6` last turn; do the symmetric cleanup here for consistency.

#### 2. Audit for other orphan `_version.py` files in asimov

`find asimov/src -name '_version.py'` and confirm each one is either (a) imported and stamped by a `make version` target, or (b) deleted. The `asimov/src/asimov/io/_version.py` is the one already known to be orphaned; there may be others in `asimov.net`, `asimov.base`, `asimov.modules`, `asimov.playingcard` (the latter four all have their own pyprojects per `asimov/src/asimov/{net,base,modules,playingcard}/pyproject.toml`).

#### 3. Add a `make version` target to asimov

Either at `asimov/Makefile` (project root) or `asimov/src/Makefile` (sibling pattern), mirroring `bed/src/Makefile:30-34`:

```make
version:
	@echo '__version__ = "0.0.1.dev$(VERSION)"' > asimov/_version.py
	@echo 'githash = "'`git log -1 --format='%H' 2>/dev/null | cut -c 1-16`'"' >> asimov/_version.py
	@echo 'datestamp = "$(VERSION)"' >> asimov/_version.py
	@cat asimov/_version.py
```

…with `__datestamp__` (with underscores) if matching the `bbsengine6` scheme, or `datestamp` (without) if matching the `bed`/`zoid6`/`empyre`/`murdermotel` scheme. Pick one and be consistent across the monorepo — the current divergence (some packages use `__datestamp__`, some use `datestamp`) is a separate cleanup that could go in a sibling TODO.

#### 4. Re-export `__version__` from `asimov/__init__.py`

Mirror the pattern just established in `bbsengine6/py/src/bbsengine6/__init__.py`:

```python
from ._version import __version__, __datestamp__
```

…so `import asimov; asimov.__version__` works and is guaranteed to match the wheel's published version.

### Decisions

- [ ] Pick (a), (b), or (c) for the orphan `asimov/io/_version.py` cleanup.
- [ ] Audit and either stamp or delete every `_version.py` under `asimov/src/`.
- [ ] Add `make version` target to asimov's Makefile.
- [ ] Re-export `__version__` (and `__datestamp__` or `datestamp`, depending on choice) from `asimov/__init__.py`.
- [ ] Cross-monorepo: settle on one of `__datestamp__` or `datestamp` and migrate the other packages. Tracked separately.

### Cross-references

- `bed/TODO.md` — uses `__version__`, `githash`, `datestamp` (no underscores) in `bed/src/bed/_version.py:1-3`.
- `zoid6/src/zoid6/_version.py` — same scheme as `bed`.
- `bbsengine6/py/src/bbsengine6/_version.py` — uses `__version__`, `githash`, `__datestamp__` (with underscores) after the 2026-06-26 cleanup.
- `empyre/src/empyre/_version.py` — same as `bed`/`zoid6` (no underscores on `datestamp`).

## Build infrastructure

- [ ] PREPARE_BUILD protection for in-tree `build/` (@since 20260820)
  - Problem: `asimov/Makefile` `build` target (line 19) runs `python -m build --outdir dist` from the project root. There is no `PREPARE_BUILD` macro before the invocation, so a foreign-owned in-tree `build/` would cause setuptools to EPERM on the `chown` it does when populating `dist-info/`. (Pre-existing, more fundamental bug: asimov has no top-level `pyproject.toml` and no `src/asimov/pyproject.toml` either — `python -m build` from the project root will fail with "no pyproject.toml found" regardless. Fix that layout issue first, then add PREPARE_BUILD.)
  - Solution: when asimov is migrated to the standard single-pyproject layout, add a `PREPARE_BUILD` macro mirroring `bed/Makefile:163-185` and call it before the `python -m build` line.
  - Cross-ref: `bed/Makefile:163-185`, `zoid6/TODO.md` "PREPARE_BUILD standardization".

