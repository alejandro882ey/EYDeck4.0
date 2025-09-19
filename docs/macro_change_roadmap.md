## Macro Dashboard — Inventory & Roadmap

This document inventories the backend and frontend pieces involved in the main Macro dashboard view and provides a step-by-step roadmap to implement the requested UI and data changes: remove decimals, and add two small values under the main metric in each Macro card: "Año Anterior" and "Promedio".

> NOTE: This is strictly planning. No code changes are included. Implementation steps reference probable files and modules based on the project context.

---

## 1) Inventory — Backend and Frontend Functionalities (Macro view)

High-level: the Macro section shows high-level KPIs (ANSR, Horas Cargadas, RPH, Margin) for both YTD and MTD with a big numeric value, a small goal/goal-tracker bar underneath, and supporting metadata (period selector, date, filters).

- Frontend (templates + static JS/CSS)
  - `templates/core_dashboard/dashboard.html` (or template referenced by `dashboard_view`) — primary HTML that renders Macro cards and includes the goal tracker bar and number formatting.
  - Card components (likely partial templates or blocks) — responsible for rendering:
    - big numeric value (current value),
    - goal tracker bar (goal vs. actual),
    - supporting labels (unit, period)
  - Frontend formatting/JS
    - small JS functions or template filters to format numbers (thousands separators, decimals) — may live in `templates` or `static/` directory (CSS/JS). Template filters might be custom (e.g., `core_dashboard/templatetags`).
  - CSS that controls spacing so the new two small lines should sit between the big number and the goal tracker bar.

- Backend (views, services, and data sources)
  - `core_dashboard/views.py` or a view function named `dashboard_view()` — orchestrates assembling metrics for the Macro cards. This is the main entry point for the Macro data.
  - Services / business logic
    - `core_dashboard/data_processor.py`, `core_dashboard/utils.py`, or dedicated modules (e.g., `core_dashboard/modules/mtd_module.py`, `mtd_module`) — compute MTD and YTD values.
    - `ey_analytics_engine.py` — provides time-series calculations and helpers used across dashboard aggregations (may be called for forecasting or normalized values).
    - `core_dashboard/modules/facturacion/services.py` and `core_dashboard/modules/cobranzas/services.py` — examples of modules that compute aggregated DF and expose `get_all_processed_df()` style functions and use persistent caching.
  - Data sources
    - `RevenueEntry` model and related models inside `core_dashboard/models.py` — canonical source for revenue rows.
    - Processed uploads via `process_uploaded_data.py` and management commands (uploads stored under `MEDIA_ROOT/historico_de_final_database/<date>/`).
    - Engagement List: canonical column mapping (e.g., `FYTD_ANSRAmt (Sintético)` and `Perdida Dif. Camb.`) — upstream upload column names affect metric values.

- Caching & invalidation
  - Persistent caches for heavy modules (e.g., cobranzas/facturacion) written to `MEDIA_ROOT/*_combined_cache.pkl`. The project has an enhanced cache metadata format which may include a `code_hash` alongside file mtimes to force rebuilds when code changes.
  - Cache helpers: `core_dashboard/modules/shared/cache_utils.py` and module-specific cache-handling code.

- Tests
  - Unit tests for processing and modules: `core_dashboard/test_process_uploaded_data.py` and modules' tests.
  - Higher-level tests: `tests/` folder and root-level tests (e.g., `test_diana*.py`) — useful references for style.

---

## 2) Requirements / Acceptance Criteria (for the requested UI changes)

- Display rules
  - All Macro card numeric values must be shown with NO DECIMALS (integers). Thousands separators can remain.
  - For each Macro card (ANSR YTD, Horas Cargadas (YTD), RPH, Margin, ANSR MTD, Horas Cargadas (MTD), RPH MTD, Margin MTD): add two small lines under the big value and above the goal tracker bar:
    1. "Año Anterior": value for the same date in the previous year.
    2. "Promedio": the average of the present value and the previous-year value across that date range (described more precisely below).
  - The two lines are small, subdued text (visual spec to match existing micro-labels). They must be internationalized (i18n) with Spanish labels exactly "Año Anterior" and "Promedio".
  - Visual/pill specification (new request):
    - Display each item as a small pill directly under the big number and above the goal tracker bar.
    - "Año Anterior" pill: red background, white text, rounded pill shape (compact). Use the exact label `Año Anterior`.
    - "Promedio" pill: blue background, white text, rounded pill shape (compact). Use the exact label `Promedio`.
    - Pills should be small and unobtrusive (font-size equal to or slightly smaller than existing micro-labels). On narrow screens stack vertically or collapse into a single line with a small separator.
    - Provide CSS variables or classes to match existing theme colors, for example `.macro-pill--red` and `.macro-pill--blue`. Ensure accessibility: sufficient color contrast and aria-labels.

- Data behavior
  - "Año Anterior" must fetch the value for the same reporting date/day in the prior year (if the present view is YTD or MTD, compute previous-year YTD/MTD consistent with how the current metric is computed).
  - "Promedio" = average of current metric and previous-year metric across the same reporting window (i.e., (current + previous_year) / 2). Round according to the no-decimals rule.
  - If previous-year value is missing or upload not provided, fallback behavior:
    - Show a clear placeholder such as `-` or `N/A` (do not crash).
    - Promedio when previous-year missing = current (or `N/A` depending on product decision). Recommend: use `N/A` for Promedio unless instructed otherwise.

- Performance
  - For heavy queries, reuse existing caches (module-level persistent cache). Add cache keys that include year and date-range parameters.
  - Respect the project's code-hash invalidation logic so that caches rebuild when module code changes.

---

## 3) Data contract (small contract for backend → frontend)

Design a single, minimal JSON/templating contract returned by the `dashboard_view` (or service) for Macro cards. This contract can be returned in the template context (Django view) or as a JSON endpoint used by AJAX.

- Suggested data shape (per-card):

  {
    "id": "ansr_ytd",
    "label": "ANSR YTD",
    "value": 12345,             # integer (no decimals)
    "unit": "USD" or "%",    # optional
    "goal": 15000,              # integer
    "anio_anterior": 11000,     # integer or null
    "promedio": 11622,          # integer or null
    "tooltip": "...optional explanation...",
  }

- Error modes and fallbacks:
  - If `anio_anterior` is null, frontend shows `-` and Promedio shows `N/A` unless previous-year rule chosen otherwise.
  - All numeric fields typed as integers in the JSON (no float decimals).

---

## 4) Edge cases and rules to decide before implementation

- Date alignment rules
  - Clarify whether the daily snapshot uses calendar date or fiscal calendar. Implementation must match how MTD/YTD are currently computed (refer to `mtd_module`/fiscal calendar helpers).

- Missing previous-year upload
  - The user will upload the previous year document later — the code must gracefully behave when that document is missing.

- Small-number display: rounding
  - Use standard rounding (round-half-away-from-zero or Python round?) — recommend `round()` to nearest int with explicit rule (e.g., round half up). Note: Python's round ties-to-even; choose the convention and document it.

---

## 5) Roadmap — step-by-step (planning only)

Phase A — Design & Data Contract (owner: backend developer)
  1. Analyze `dashboard_view()` and identify where Macro card metrics are assembled (file: `core_dashboard/views.py` and/or `core_dashboard/data_processor.py`). Confirm current MTD/YTD computation functions and where to add previous-year calls.
  2. Define exact date-range mapping for previous-year (calendar vs. fiscal). Document in code comments.
  3. Design service functions:
     - `get_previous_year_metric(metric_key, current_date_or_range) -> Optional[Decimal]`
     - `get_promedio(metric_key, current_value, previous_value) -> Optional[int]`
  4. Add design notes for caching (cache key should include metric_key, date_range, and module_code_hash if persistent cache used).
  5. Agree on rounding policy (recommendation: round half away from zero; document and include tests).

Phase B — Backend Implementation (owner: backend developer)
  1. Implement service functions in `core_dashboard/services/macro_service.py` (or the appropriate existing service module). Keep API small and testable.
  2. Update `dashboard_view` to include `anio_anterior` and `promedio` for each macro card in the template context/JSON.
  3. Update caching logic if needed (store computed previous-year values in persistent cache with clear invalidation rules). Reuse `core_dashboard/modules/shared/cache_utils.py`.
  4. Add unit tests: happy path, missing previous-year data, zero values, large numbers.

Phase C — Frontend Implementation (owner: frontend developer)
  1. Update macro card template to render two small lines under the big number and above the goal tracker bar. Keep styles consistent with existing small-label design.
     - Use pill UI for the two items (red pill for `Año Anterior`, blue pill for `Promedio`). Place them between the main number and the goal tracker bar. Provide classname hooks:
       - `.macro-pill` (base), `.macro-pill--red`, `.macro-pill--blue`.
     - Example DOM placement (conceptual):
       - <div class="macro-card">
         ...existing big number...
         <div class="macro-pill-row">
           <span class="macro-pill macro-pill--red">Año Anterior: <strong>10,500</strong></span>
           <span class="macro-pill macro-pill--blue">Promedio: <strong>11,423</strong></span>
         </div>
         ...existing goal tracker bar...
       - Ensure markup uses microcopy and aria-labels for screen readers.
  2. Ensure number formatting enforces integer display (no decimals). Implement server-side rounding and frontend formatting should not reintroduce decimals.
  3. Add i18n strings for `Año Anterior` and `Promedio`.
  4. Add responsive checks so the two-line addition doesn't break mobile layout. Consider collapsing to a single line or tooltip at very small widths.
  5. Add a feature-flag or test hook if you want to toggle the new two-line display during rollout.

Phase D — QA, Tests & Release
  1. Run unit tests and integration tests. Add test fixtures that include previous-year dataset.
  2. Smoke test the dev server on port 8001 (`python manage.py runserver 8001`) and verify Macro section values render correctly.
  3. Visual verification across breakpoints and browsers.
  4. Add changelog entry and documentation in `docs/` (this file).

Phase E — Follow-ups
  - Add logging when previous-year data is missing or when the cache is used/invalidated for observability.
  - Add automated tests to assert cache invalidation when module code changes (re-use the existing code-hash logic).

---

## 6) Minimal acceptance tests (manual or automated)

1. Given current value = 12,345.67 and previous-year = 10,500.25, UI should display:
   - Big number: 12,346 (rounded to nearest integer) — no decimals.
   - Año Anterior: 10,500
   - Promedio: round((12,346 + 10,500) / 2) = 11,423

2. If previous-year missing, Año Anterior shows `-` and Promedio shows `N/A` (or agreed fallback).

3. Performance: with large dataset make sure adding previous-year computations does not add > 200ms latency to the Macro page load (target depends on current baseline; measure and optimize if needed).

---

## 7) Notes & assumptions

- Assumptions made while planning:
  - Macro card templates are served from `templates/core_dashboard/` and orchestrated by `dashboard_view()`.
  - MTD/YTD computations are centralized in mtd/fiscal modules or `ey_analytics_engine.py`.
  - The previous-year upload the user will provide later will be mapped into the same models/columns used for the current data (Engagement List mapping applies).

- Items requiring confirmation from product or data owner before coding:
  1. Exact rounding rule for all metrics (ties-to-even vs half-away-from-zero).
  2. Promedio fallback behavior when previous-year is missing.
  3. Mobile UX preference for stacked small-lines vs tooltip.

---

## 8) Next steps (what I will do when you say "go")

1. Implement Phase A design artifacts in code: add service method stubs and tests.
2. Implement Phase B & C following the roadmap above, run unit tests and smoke test `runserver 8001`.
3. Deliver a PR with the changes and a short README describing how to trigger a cache rebuild and where to upload the previous-year file.

---

If you want, I can now:
- expand the data-shape to include examples for each Macro card,
- prepare unit test skeletons for backend computations,
- or wait until you upload the previous-year document and then map its columns.

Tell me which next step you prefer.

---

## Cache risks analysis & mitigations (critical for reliable dashboard loads)

I inspected the cache-heavy modules (`core_dashboard/modules/cobranzas/services.py`, `core_dashboard/modules/facturacion/services.py`) and the shared helper `core_dashboard/modules/shared/cache_utils.py`. Below are concrete failure modes that can make the dashboard slow, unresponsive, or fail to load, with recommended mitigations and operational workarounds.

1) Long/blocking cache rebuild on first request
   - Why it happens: `get_all_processed_df()` reads and processes every processed workbook in the module media folder. If the persistent cache is missing or stale, the request thread will rebuild the combined DataFrame synchronously (I/O + CPU heavy). On the Django dev server this can block the request and make the page appear as "not loading".
   - Files: `cobranzas/services.py::get_all_processed_df`, `facturacion/services.py::get_all_processed_df`.
   - Mitigation:
     - Precompute caches during deployment or via a management command (pre-build caches on CI or a start-up script) instead of rebuilding on the first web request.
     - Offload cache builds to a background worker (Celery, RQ) and have the web UI show a light-weight "building preview" state until ready.
     - Add a short, non-blocking fast-path: if rebuild would take longer than X ms, return a lightweight summary (totals) and trigger an async rebuild.

2) Corrupted or malicious pickle file causes errors or security risk
   - Why it happens: persistent caches are pickled DataFrames. `pickle.load()` can raise exceptions on corruption and is unsafe for untrusted input (pickle executes arbitrary code on load).
   - Files: `cobranzas/services.py`, `facturacion/services.py` (both use `pickle.load`).
   - Mitigation:
     - Add a small header/version + checksum to cache files (or write a tiny metadata JSON alongside the binary cache) and validate before unpickling.
     - On pickle errors, log the full exception, remove the cache file, and fall back to rebuild (already partially implemented; make the removal explicit and logged).
     - Prefer safer on-disk formats: store pre-aggregated numeric summaries as JSON or CSV, or use Parquet for DataFrames (pandas.to_parquet / read_parquet). Parquet is safer (no arbitrary code execution) and often faster for large DataFrames.

3) Large memory usage / OOM when unpickling huge DataFrames
   - Why it happens: a large cached DataFrame is entirely loaded into memory when unpickled; for low-memory containers or dev machines this can crash the process.
   - Mitigation:
     - Don't cache entire raw DataFrames if the UI only needs aggregates; cache aggregated numbers and small lookup tables instead.
     - If full DF is needed, store on-disk columnar format (Parquet) and read only required columns or use stream processing.
     - Add defensive checks: if cache file is larger than a configured threshold (e.g., 200 MB), skip direct unpickle and rebuild in a controlled, memory-aware way.

4) Concurrent write / race conditions on cache file
   - Why it happens: multiple requests or processes may attempt to rebuild and write the same cache `.tmp` file simultaneously.
   - Files: writing tmp file and os.replace in both services.
   - Mitigation:
     - Use per-process unique temp filenames (include PID/timestamp/uuid) instead of a single fixed `.tmp` name, then atomically replace the target cache file with the temp file.
     - Add advisory file locks (cross-platform helpers like `portalocker`) during write and while deciding to read/write the cache.
     - Use an in-process threading.Lock when running under a threaded WSGI server to avoid races on the in-memory attributes `self._cached_df/_cached_mtime`.

5) File-system oddities (OneDrive, network mounts, permissions)
   - Why it happens: the repository and likely `MEDIA_ROOT` are on OneDrive in this environment. OneDrive sync, locks or network latency can cause partial writes, slow I/O or permission errors when deleting/replacing cache files.
   - Mitigation:
     - For caches, prefer a local, non-synced directory (e.g., `/tmp`, or a dedicated `MEDIA_ROOT` outside OneDrive). Document this in deployment notes.
     - Add retry/backoff when removing or renaming files (Transient errors should retry a small number of times and then fail gracefully).

6) Code-hash computation failure or slowness
   - Why it happens: `compute_files_hash()` inspects module files; if it fails it falls back to mtime-based invalidation. If it reads too many files or hits unreadable files it may be slow.
   - Files: `core_dashboard/modules/shared/cache_utils.py` and callers in services.
   - Mitigation:
     - Limit file collection to top-level `.py` files (already implemented) and cache the computed code-hash in a small metadata file to avoid recomputing on every service init.
     - Make code-hash optional (feature flag) and fall back to mtime-only invalidation where acceptable.

7) Silent exceptions and poor observability
   - Why it happens: many cache-clearing and loading operations swallow exceptions (`except Exception: pass`) without logging. This can hide the real root cause when the dashboard doesn't load.
   - Mitigation:
     - Replace silent `pass` with logging at warning/error level including stack traces so operators can triage quickly.
     - Add metrics/log counters: cache_load_time, cache_rebuild_time, cache_failures, cache_invalidations.

8) Thread-safety of in-memory cache
   - Why it happens: `self._cached_df` and `self._cached_mtime` are modified and read without locks; under multi-threaded servers this can produce races and inconsistent reads.
   - Mitigation:
     - Guard reads/writes with a short-lived threading.Lock (or per-instance lock attribute) to ensure consistent behavior under concurrency.

9) Pickle format/version compatibility across pandas/Python upgrades
   - Why: pickled DataFrames depend on pandas/python versions. Upgrading Python/pandas may make old pickles unreadable (or worse, produce strange failures).
   - Mitigation:
     - Store a small metadata file with pandas/python version used to produce cache; on mismatch either rebuild cache or migrate safely.
     - Prefer cross-version on-disk formats (Parquet/Feather/CSV) for long-lived caches.

Quick operational remediation steps (what to run when dashboard fails to load)
  - Delete persistent caches (this workspace already includes small scripts):
    - `scripts/delete_persistent_cache.py` or manually remove `media/cobranzas/cobranzas_combined_cache.pkl` and `media/facturacion/facturacion_combined_cache.pkl`.
  - Clear in-memory and compiled caches:
    - Restart the Django server (dev server) to clear in-memory caches.
  - Prebuild caches on a fast machine (recommended): run a one-off script that imports the service module and calls `get_all_processed_df()` so the expensive rebuild happens offline.

Implementation checklist for safe cache changes
  - [ ] Add robust logging around every load/remove/write of persistent cache files.
  - [ ] Use unique temp filenames and optional advisory locking when writing cache files.
  - [ ] Add a small management command `management/commands/prebuild_caches.py` that iterates modules and builds persistent caches.
  - [ ] Add a dev config flag `DISABLE_PERSISTENT_CACHES=True` to skip disk caches when desired.
  - [ ] Replace `pickle` DataFrame cache with Parquet or store only pre-aggregated summaries unless full DF is required.
  - [ ] Add unit tests that simulate corrupted cache files, concurrent writes, and OneDrive/permission errors.

If you want, I can now implement a non-invasive safety patch (planning + code) that does one or more of the following:
  - Add logging around cache load failures and delete corrupted cache files automatically,
  - Add a `management/commands/prebuild_caches.py` that precomputes caches for `cobranzas` and `facturacion`, or
  - Replace pickle-based cache write/read with Parquet (small, low-risk change) for one module as a proof-of-concept.

Tell me which mitigation you'd like me to implement first and I'll add it to the todo list and start the change (I'll run tests and a smoke run of the dev server).

---

## Finalized implementation plan (developer-ready)

This section removes ambiguity and lists explicit steps, file edits, tests, and verification steps so a developer can implement the Macro UI change (no-decimals + two pills) and the recommended cache-safety mitigations with minimal additional questions.

Decisions taken (explicit defaults used in the implementation):
- Rounding rule: Round half away from zero (ROUND_HALF_UP). Server computes integers (no decimals) before sending to templates. Use Python Decimal for rounding to avoid ties-to-even behavior.
- Promedio fallback: If previous-year value is missing, show `Promedio` as `N/A` and `Año Anterior` as `-`.
- Pill UI: red pill for `Año Anterior`, blue pill for `Promedio`, white text, use classes `.macro-pill`, `.macro-pill--red`, `.macro-pill--blue`.
- Initial cache mitigation (first PR): non-invasive safety patch that (A) adds logging around cache load failures and (B) adds a management command `prebuild_caches` to precompute persistent caches. This reduces risk immediately without changing cache formats.

High-level milestones (ordered, each with exact tasks):

1) Backend: service API & computations (files to modify)
  - Files to edit:
    - `core_dashboard/services/macro_service.py` (create this file if not present) — add the core functions and tests.
    - `core_dashboard/views.py` — update `dashboard_view()` to include the new fields in the template context for each Macro card, following the data contract.
    - `core_dashboard/modules/cobranzas/services.py` and `core_dashboard/modules/facturacion/services.py` — add optional log statements around cache `pickle.load` and cache removal paths (non-invasive).
  - Backend tasks (detailed):
    1. Create `core_dashboard/services/macro_service.py` with:
       - get_metric(metric_key, date_range) -> Decimal
       - get_previous_year_metric(metric_key, date_range) -> Optional[Decimal]
       - get_promedio(metric_key, current_value, previous_value) -> Optional[int]
       Implementation details:
         - `get_previous_year_metric` reuses existing MTD/YTD functions (call into `mtd_module`, `ey_analytics_engine` or existing helper functions used by `dashboard_view`). If those helpers aren't available as services, extract the aggregation code into `macro_service` and call them.
         - `get_promedio`: If previous_value is None, return None; otherwise compute (current + previous)/2 and round using Decimal ROUND_HALF_UP to nearest integer.
    2. Update `dashboard_view` to call the macro service and for each card add keys: `anio_anterior` (int|null) and `promedio` (int|null). Example context entry per card: `{'id':'ansr_ytd','value':12345,'anio_anterior':10500,'promedio':11423,...}`.
    3. Server-side rendering must ensure all numbers are integers. The template should display integers and not format with decimal places.

2) Frontend: template + CSS changes (files to modify)
  - Files to edit:
    - `templates/core_dashboard/dashboard.html` (or the partial used for macro cards). If Macro cards are partials, update that template file.
    - Optionally: `static/css/core_dashboard.scss` or the project's main CSS file — add pill classes.
  - Frontend tasks (detailed):
    1. Insert pill markup between the main metric and the goal tracker bar. Use the DOM structure (example):
       - <div class="macro-card" role="group" aria-label="ANSR YTD">
         ...existing big number markup...
         <div class="macro-pill-row">
           {% if card.anio_anterior is not None %}
             <span class="macro-pill macro-pill--red" aria-label="Año Anterior">Año Anterior: <strong>{{ card.anio_anterior|intcomma }}</strong></span>
           {% else %}
             <span class="macro-pill macro-pill--red" aria-hidden="true">Año Anterior: <strong>-</strong></span>
           {% endif %}
           {% if card.promedio is not None %}
             <span class="macro-pill macro-pill--blue" aria-label="Promedio">Promedio: <strong>{{ card.promedio|intcomma }}</strong></span>
           {% else %}
             <span class="macro-pill macro-pill--blue" aria-hidden="true">Promedio: <strong>N/A</strong></span>
           {% endif %}
         </div>
         ...existing goal tracker bar markup...
       - Ensure `intcomma` or equivalent template filter is used to keep thousands separators.
    2. Add CSS (SCSS) rules to match existing theme variables (example snippet to place in the CSS file):
       - .macro-pill-row { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; flex-wrap: wrap; }
       - .macro-pill { padding: 3px 8px; border-radius: 999px; font-size: .775rem; color: #fff; display: inline-block; }
       - .macro-pill--red { background: var(--ey-red,#d9534f); }
       - .macro-pill--blue { background: var(--ey-blue,#0275d8); }
       - Add responsive breakpoint: on narrow widths, stack pills vertically (.macro-pill-row { flex-direction: column; }).
    3. Add i18n strings to `locale` files for `Año Anterior` and `Promedio`.

3) Cache safety (non-invasive initial changes)
  - Files to edit:
    - `core_dashboard/modules/cobranzas/services.py` — add logging when `pickle.load` fails and remove the cache file with a logged warning.
    - `core_dashboard/modules/facturacion/services.py` — same as above.
    - Add new management command `core_dashboard/management/commands/prebuild_caches.py`.
  - Tasks (detailed):
    1. Wrap `pickle.load(fh)` in try/except; on exception log stack trace at WARNING, attempt to `os.remove(cache_file)` (log success/failure), and continue (rebuild from files). This prevents a corrupted cache from causing persistent load failures.
    2. Use unique temp filenames when writing caches (already used `.tmp` suffix — update to include process id and timestamp, e.g., `f"{cache_file}.tmp.{os.getpid()}.{int(time.time())}"`).
    3. Add `prebuild_caches` management command which imports service classes and calls `get_all_processed_df()` for `cobranzas` and `facturacion`. Document how to run the command in the README.

4) Tests (exact files to create)
  - Unit tests:
    - `core_dashboard/tests/test_macro_service.py` — tests for `get_previous_year_metric`, `get_promedio` including rounding and fallback rules.
    - `core_dashboard/modules/cobranzas/test_cache_behaviour.py` — simulate corrupted cache pickle and ensure service removes it and rebuilds.
    - `core_dashboard/modules/facturacion/test_cache_behaviour.py` — same as above.
  - Integration / Template tests:
    - `core_dashboard/tests/test_dashboard_view.py` — render `dashboard_view` with a mocked macro_service to verify pills render with correct text and CSS classes, and no decimals appear.

5) QA & verification steps (manual and automated)
  - Automated:
    - Run unit tests: `pytest -q` (or the project's test runner). Ensure new tests pass.
    - Run linters: `flake8` and formatting `black --check` if used in CI.
  - Manual smoke tests (on dev machine):
    1. Ensure `MEDIA_ROOT` contains processed `cobranzas` and `facturacion` example files (or run upload flows).
    2. Run prebuild caches: `python manage.py prebuild_caches` (this will create persistent caches so the first web request is fast).
    3. Start dev server on mandated port 8001:

```powershell
python manage.py runserver 8001
```

    4. Open `http://127.0.0.1:8001` and verify:
       - Macro cards show integers (no decimals),
       - Each card contains two pills between the main number and the goal tracker,
       - `Año Anterior` shows previous year integer or `-`, `Promedio` shows integer or `N/A`.
    5. Trigger upload of a new `cobranzas` file and verify cache is invalidated and the Macro page still loads (prebuild reduces blocking risk).

6) Rollout plan & rollback
  - Rollout steps:
    1. Create a feature branch and implement the backend service + frontend template + CSS + tests.
    2. Run unit tests locally and on CI.
    3. Merge to staging; run `python manage.py prebuild_caches` on staging host.
    4. Smoke test staging and run a sampling of dashboards.
    5. Deploy to production during a low-traffic window.
  - Rollback steps (if dashboard fails):
    - Revert the PR commit on the server (git revert or redeploy previous tag).
    - If failure is related to persistent caches, remove `media/*_combined_cache.pkl` files and restart server.

7) PR checklist (what to include in the pull request)
  - Code changes:
    - `core_dashboard/services/macro_service.py` with well-documented functions and type hints.
    - `core_dashboard/views.py` updated to include new fields in template context.
    - Template updates in `templates/core_dashboard/dashboard.html`.
    - CSS updates (SCSS/CSS) with comments referencing `.macro-pill` classes.
    - Non-invasive cache safety edits in `cobranzas` and `facturacion` services.
    - New management command `prebuild_caches`.
  - Tests: unit tests and integration tests added.
  - Docs: update `docs/macro_change_roadmap.md` (this file updated) and add short README snippet describing `prebuild_caches` and cache cleanup instructions.
  - CI: ensure tests run and pass.

8) Acceptance tests (explicit final checks to pass before merge)
  - All unit tests pass locally and in CI.
  - Dashboard page loads within an acceptable latency (compare to baseline). If baseline unknown, target < 1s for Macro render on warm caches; for cold rebuild, ensure request doesn't hang indefinitely (use timeout/async rebuild plan if needed).
  - Visual check: pills present for each Macro card, colors match design, text follows i18n and accessibility rules.
  - Cache behavior: corrupted cache file is removed and rebuild happens (simulate by writing garbage to the cache file then restarting server and observing logs).

9) Follow-ups (post-merge improvements)
  - Replace pickle caches with Parquet and/or store aggregates instead of full DataFrames.
  - Add metrics and logs to application monitoring (Prometheus/Datadog) for cache metrics.
  - Add concurrency tests for cache writes (simulate multiple workers rebuilding caches simultaneously).

---

If you'd like, I can implement the initial non-invasive safety patch + `prebuild_caches` management command now (low risk). I will:
- mark the corresponding todo as in-progress,
- implement the changes (small edits to `cobranzas` and `facturacion` services, and add the management command),
- add unit tests for the cache error case, and
- run the test suite and a dev-server smoke test on port 8001.

Tell me to proceed with that first step or pick another item from the PR checklist to implement first.
