# Repository Improvement Plan

This document outlines a tiered roadmap for cleaning up and hardening the aimbot codebase. Each tier builds on the previous one and is designed to be tackled independently.

---

## Tier 1 — Quick Wins (minutes each)

These are low-risk, one-line changes that remove immediate hazards and cruft. No architectural changes required.

### 1.1 Remove `breakpoint()` calls left in production

Three files have `breakpoint()` statements that will hang the process if run outside a debugger:

| File | Line |
|---|---|
| `aimbot-backend/aimbot/scrapers/news/ge_wp.py` | 103 |
| `aimbot-backend/aimbot/radio/elabs.py` | 41 |
| `aimbot-backend/aimbot/scrapers/family_notices.py` | 126 |

### 1.2 Remove `from unittest import result` in weather.py

`aimbot-backend/aimbot/scrapers/weather.py:6` — IDE autocomplete accident. Delete the line.

### 1.3 Remove unused imports

| File | Import |
|---|---|
| `aimbot-backend/aimbot/radio/elabs.py:5` | `from elevenlabs import save` |
| `aimbot-backend/aimbot/radio/radio_news.py:8` | `from elevenlabs import ElevenLabs` |
| `aimbot-backend/aimbot/scrapers/weather.py:6` | `from unittest import result` |

### 1.4 Delete dead code: `merge_with_cache()` in cache.py

`aimbot-backend/aimbot/cache.py:101-125` — Defined but never called. The actual cache merging is done inline (and duplicated) in `main.py`. Either delete it or adopt it consistently (see Tier 2).

### 1.5 Fix missing `@pytest.mark.asyncio` decorators

`aimbot-backend/tests/test_news.py:18,30` — `test_ge_scraper` and `test_jep_scraper` are `async def` without the decorator, so pytest-asyncio silently skips them.

### 1.6 Remove commented-out dead code

- `aimbot-backend/aimbot/scrapers/news/ge.py:104` — commented-out test code
- `aimbot-backend/aimbot/scrapers/news/ge_wp.py:44-46` — commented-out debug code
- `aimbot-backend/aimbot/scrapers/news/ge_wp.py:103` — (same as 1.1)
- `aimbot-frontend/src/routes/+layout.svelte:7,9` — commented-out CSS imports

### 1.7 Fix empty homepage

`aimbot-frontend/src/routes/+page.svelte` — Completely empty file. Navigate to `/` and users see a blank white page. Either add content (a welcome page or redirect) or redirect to a default email page.

### 1.8 Add missing `.gitignore` entries

Add to root `.gitignore`:
```
node_modules/
.svelte-kit/
*.log
.vscode/
.idea/
.env.*
```

### 1.9 Move `@types/lodash` from `dependencies` to `devDependencies`

`aimbot-frontend/package.json:26` — Type definitions belong in `devDependencies`.

### 1.10 Remove unused dependency: `@sveltejs/adapter-auto`

`aimbot-frontend/package.json:15` — Listed in `devDependencies` but never imported or used.

### 1.11 Add `engines` field to package.json

`aimbot-frontend/package.json` — `.npmrc` has `engine-strict=true` but no engines declared, making it a no-op. Add:
```json
"engines": { "node": ">=18" }
```

### 1.12 Fix `prepare` script masking errors

`aimbot-frontend/package.json:10` — `"svelte-kit sync || echo ''"` silently swallows all failures. Use `"svelte-kit sync"` and handle errors explicitly, or at minimum log the failure.

---

## Tier 2 — Short-Term Improvements (hours each)

These require modest refactoring but deliver significant quality gains. Each is self-contained.

### 2.1 Fix `main.py` exposing Python tracebacks to clients

`aimbot-backend/aimbot/main.py:89-91` — `except Exception as e` returns raw `str(e)` (and sometimes implicit tracebacks) via HTTP 500 responses. This leaks internal paths and stack traces.

**Fix:** Log the full exception server-side, return a generic `{"detail": "Internal server error"}`:
```python
import logging
logger = logging.getLogger(__name__)

except Exception:
    logger.exception("Failed to fetch email %s", email_type)
    raise HTTPException(status_code=500, detail="Internal server error")
```

### 2.2 Fix `soup.url` AttributeError in JEP scraper

`aimbot-backend/aimbot/scrapers/news/jep.py:58` — `soup.url` doesn't exist on BeautifulSoup objects. Should be `response.url` (the `aiohttp` response object).

### 2.3 Fix `except:` bare except in JEP scraper

`aimbot-backend/aimbot/scrapers/news/jep.py:47` — Bare `except:` catches `KeyboardInterrupt` and `SystemExit`. Change to `except Exception:` at minimum.

### 2.4 Fix cross-platform `%-d` strftime format

`aimbot-backend/aimbot/main.py:123` — `%-d` is platform-specific (fails on Windows). Replace with:
```python
f"{datetime.now().day} {datetime.now().strftime('%B %Y')}"
```

### 2.5 Fix `business_stories[0]` IndexError

`aimbot-backend/aimbot/main.py:222` — Array access without bounds check. Wrap in a conditional or use `next(iter(business_stories), None)`.

### 2.6 Extract duplicated cache merge logic

`aimbot-backend/aimbot/main.py:134-137, 175-178, 196-198, 211-213, 228-230` — The same `for k in fresh_data.keys(): if not fresh_data[k]: fresh_data[k] = cached[k]` is repeated 5 times. Either use the existing `merge_with_cache()` from `cache.py` or create a shared helper.

### 2.7 Consolidate duplicated scrapers

`aimbot-backend/aimbot/scrapers/news/be.py` and `ge.py` are ~95% identical. `be_wp.py` and `ge_wp.py` are ~95% identical. Create base classes:
- `LegacyScraper` → inherit `BE`/`GE` with only the URLs/differentiators overridden
- `WordpressScraper` → inherit `BEWordpress`/`GEWordpress` with only category IDs/class names overridden

### 2.8 Share `aiohttp.ClientSession` across requests

`aimbot-backend/aimbot/scrapers/news/base.py:56-59` — Creates a new session per request, which means a new connection pool each time. Accept an optional session parameter or use a session manager at the caller level.

### 2.9 Make weather requests concurrent

`aimbot-backend/aimbot/scrapers/weather.py:42-69` — Weather and tide API calls run sequentially. Use `asyncio.gather` since they're independent.

### 2.10 Replace `print()` with `logging` in cache.py

`aimbot-backend/aimbot/cache.py:41, 68, 87` — Three `except` blocks use `print()` which bypasses structured logging. Use `logging.warning(...)` or `logging.error(...)`.

### 2.11 Add error handling to Jinja2 template rendering

`aimbot-backend/aimbot/email_renderer.py:21` — Template rendering errors surface as raw 500s with Jinja2 tracebacks. Wrap in try/except and raise `HTTPException` with a meaningful message.

### 2.12 Fix CORS configuration

`aimbot-backend/aimbot/main.py:44-48` — `allow_origins=["*"]` combined with `allow_credentials=True` is invalid. Restrict to the specific frontend origin:
```python
allow_origins=[os.getenv("ALLOWED_ORIGIN", "http://localhost:5173")],
allow_credentials=False,
```

### 2.13 Add input validation to `/api/news_stories/` endpoint

`aimbot-backend/aimbot/main.py:65-66` — The `url` parameter is barely validated (substring check for domain). This is an SSRF vector — an attacker could pass internal URLs. Use `urllib.parse` to validate the scheme + hostname whitelist.

### 2.14 Create shared API client module in frontend

All fetch calls in `EmailEditor.svelte` and `radio_news/+page.svelte` hardcode `/api/emails/`, `/api/radio/`, `/api/news_stories/`. Create a shared API client with typed methods:
```ts
export async function fetchEmail(type: EmailType): Promise<EmailData> { ... }
```

### 2.15 Fix missing leading `/` in radio_news API call

`aimbot-frontend/src/routes/radio_news/+page.svelte:24` — `fetch('api/radio/speakers')` is a relative URL that breaks on subpaths. Should be `/api/radio/speakers`.

### 2.16 Replace `alert()` calls with proper toast/error UI

`aimbot-frontend/src/lib/components/EmailEditor.svelte:56, 80, 104, 136, 151` — Five `alert()` calls block the UI thread. Create a reusable toast notification or error state component.

### 2.17 Convert Svelte 4 `$:` to Svelte 5 runes

Most components use legacy `$:` reactive declarations alongside some runes (`$props()`). Fully migrate:
- `ArrayEditor.svelte` — `$:` → `$derived` / `$effect`
- `EmailEditor.svelte` — `$:` → `$derived` / `$effect`  
- `+layout.svelte` — `onMount` → `$effect`
- `radio_news/+page.svelte` — `onMount` → `$effect`

### 2.18 Extract shared Modal component

Both `ArrayEditor.svelte` and `EmailEditor.svelte` implement their own modal dialog with duplicated HTML, CSS, and a11y issues. Create a single `<Modal>` component with keyboard handling, focus trapping, and proper ARIA attributes.

### 2.19 Fix modal a11y issues

Both modals suppress a11y warnings with `<!-- svelte-ignore -->` comments instead of fixing the underlying issues:
- Add keyboard handlers (Escape to close)
- Add `role="dialog"` and `aria-modal="true"`
- Add `role="button"` and `tabindex="0"` on clickable non-interactive elements

### 2.20 Fix `any` usage in components

`ArrayEditor.svelte` has `items: any[]` and `EmailEditor.svelte` has `emailData: any`. Use proper types from the generated `api.d.ts`.

---

## Tier 3 — Medium-Term Structural Improvements (days each)

These involve rethinking how the code is organized. Plan each as a separate PR.

### 3.1 Split `main.py` into route modules

`main.py` at 322 lines mixes route definitions, scraper instantiation, data assembly, caching, email rendering, radio/TTS, and static file serving. Split into:

```
aimbot/
  routers/
    emails.py       # /api/emails/* routes
    radio.py        # /api/radio/* routes
    scraper.py      # /api/news_stories route
  services/
    email_service.py # email fetch + assembly logic
    radio_service.py # radio script + TTS logic
```

### 3.2 Add authentication

Currently zero authentication — anyone can call the radio generation endpoint (consuming ElevenLabs credits) or overwrite cached email data. Options:
- **Simple:** Shared API key in `Authorization` header, validated via middleware
- **Better:** OIDC/SAML via FastAPI middleware for browser-based auth
- **Minimal:** At minimum protect `/api/radio/generate` and `/api/emails/*/save`

### 3.3 Add rate limiting to TTS endpoint

`/api/radio/generate` has no rate limiting — an attacker could exhaust ElevenLabs credits. Add `slowapi` or similar rate limiter.

### 3.4 Add proper logging infrastructure

Replace scattered `print()` and `console.error()` calls with a structured logging setup:
- **Backend:** Python's `logging` module with log levels and rotation
- **Frontend:** Guard `console.error` behind `import.meta.env.DEV` or use a logging service

### 3.5 Add ESLint + Prettier to frontend

No linting or formatting is configured. Add:
- `eslint` with Svelte plugin (`eslint-plugin-svelte`)
- `prettier` with `prettier-plugin-svelte`
- `lint` and `format` scripts in `package.json`

### 3.6 Add `.env.example` files

Create `.env.example` in the backend root listing all required env vars with descriptions. Currently a new developer has no reference.

### 3.7 Add type-safe discriminated unions for email models

`main.py` uses `Union[BEEmailData, GEEmailData, JEPEmailData, ...]` which FastAPI can't discriminate without a discriminator. Add a `type: Literal["be", "ge", ...]` field to each model and use `Annotated` with `discriminator`.

### 3.8 Generate and keep API types in sync

`aimbot-frontend/src/lib/types/api.d.ts:107` — `EmailType` is `"be" | "ge" | "jep"` but route pages use `"insider_gsy"`, `"insider_jsy"`, `"aimpremium"`. Either:
- Add these types to the FastAPI schema so `openapi-typescript` generates them, or
- Update the hand-maintained type if the schema can't represent them

### 3.9 Make scrapers configurable

Hardcoded values that should be in env/config:
- BBC Weather location IDs (`weather.py`)
- WordPress API base URLs (`be_wp.py`, `ge_wp.py`)
- Personal email in User-Agent (`config.py`)
- Story limits and magic numbers (`main.py`)
- TTS model name and voice settings (`elabs.py`)
- Cache directory path (`main.py`)

### 3.10 Remove the `redis` dependency (or implement it)

`pyproject.toml` lists `redis>=7.0.1` but it's never imported anywhere. Either remove it or use it to replace the JSON file cache.

### 3.11 Extract `first_sentence` filter from EmailRenderer

The Jinja2 `first_sentence` filter is a static method on `EmailRenderer` but isn't conceptually related to rendering. Move to a `filters.py` or `template_utils.py`.

### 3.12 Consolidate route wrapper pages

6 route files (`be_email`, `ge_email`, `jep_email`, `aim_premium`, `insider_jsy`, `insider_gsy`) are thin wrappers around `EmailEditor`. Consider using a single parametrized route and a config object instead of 6 nearly-identical files.

### 3.13 Add `noUncheckedIndexedAccess` to TypeScript config

`tsconfig.json` has `strict: true` but doesn't enable `noUncheckedIndexedAccess`. This means `items[0]` is typed as the element type rather than `T | undefined`, hiding potential runtime crashes.

---

## Tier 4 — Long-Term Architecture Changes (weeks)

These are major undertakings that reshape the project. Evaluate cost/benefit for each.

### 4.1 Migrate tests to use mocks

All 4 test files make real HTTP requests to external websites. They'll fail without internet, on upstream changes, or under rate limiting. Options:
- Use `aioresponses` / `pytest-aioresponses` to mock `aiohttp` calls
- Use `responses` library for sync HTTP mocking
- Add a `pytest.mark.integration` marker and run integration tests only in CI

### 4.2 Add CI/CD pipeline

No CI/CD exists. Add GitHub Actions for:
- Linting (Ruff for Python, ESLint for TypeScript)
- Type checking (`pyright`, `svelte-check`)
- Unit tests (with mocked services)
- Integration tests (on schedule, not per-commit)
- Build verification (SvelteKit static build)

### 4.3 Add frontend component tests

Zero frontend tests. Add:
- Vitest + `@testing-library/svelte` for component tests
- Playwright or Cypress for E2E smoke tests (verify each email page loads)

### 4.4 Add backend unit tests

Current tests are all integration-level. Add:
- Unit tests for `EmailRenderer`
- Unit tests for `EmailCache`
- Unit tests for model serialization/deserialization
- Unit tests for scraper parsing (feed HTML fixtures, verify parsed output)

### 4.5 Containerize for deployment

Add `Dockerfile` + `docker-compose.yml` for both backend and frontend. The backend already has the app server and SPD serves the static frontend — containerizing would make deployment reproducible.

### 4.6 Adopt SvelteKit best practices

The frontend is a static SPA using `adapter-static`. Evaluate whether:
- A full SvelteKit server (with `+server.ts` endpoints) would be better than the FastAPI API
- Or whether the SPA approach is correct but should use SvelteKit's form actions/load functions for the pages that do exist

### 4.7 Extract shared types package

The frontend `api.d.ts` is manually generated from the backend OpenAPI schema. Instead, use FastAPI's `/openapi.json` endpoint and a build step to keep types in sync automatically. Consider a monorepo tool like Turborepo or pnpm workspaces.

### 4.8 Add secrets management

Currently secrets live in an unencrypted `.env` file. For any deployment beyond local dev, use:
- Environment-level secrets (Kubernetes secrets, systemd env files, etc.)
- A secrets vault (Infisical, Doppler, HashiCorp Vault)
- At minimum, don't load `.env` in production — only in dev via `python-dotenv`

---

## Summary by Effort

| Tier | # Items | Total Est. Time | Impact |
|---|---|---|---|
| Tier 1 (Minutes) | 12 | ~2 hours | Removes bugs, dead code, security hazards |
| Tier 2 (Hours) | 20 | ~2-3 days | Fixes bugs, consolidates duplication, improves UX |
| Tier 3 (Days) | 13 | ~2-3 weeks | Structural refactors, auth, config, types |
| Tier 4 (Weeks) | 8 | ~4-6 weeks | Testing, CI/CD, deployment, architecture |
| **Total** | **53** | | |

**Recommended order:** Start at Tier 1 to make the codebase safe to work on, then pick individual Tier 2 items based on what you touch most often. Tier 3 items are best done one at a time as their own focused PRs. Tier 4 items should be planned and scoped carefully — they're projects in their own right.
