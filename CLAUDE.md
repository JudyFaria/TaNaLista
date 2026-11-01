# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Lista de Compras": shared shopping lists for mobile. It's a FastAPI backend that serves a no-build PWA frontend (vanilla ES modules). The code comments, docstrings, user-facing strings and README are in Brazilian Portuguese. Keep new text in Portuguese.

## Commands

Requires Python 3.12+. On Windows the venv lives in `.venv`.

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # app at :8000, Swagger at /api/docs

pytest                                              # all tests
pytest tests/test_services.py                       # one file
pytest tests/test_api.py::test_name                 # one test
pytest "tests/test_api.py::test_name[json]"         # one backend only (json | firestore)
```

No linter, formatter or frontend build is configured.

## Architecture

Clean architecture. Dependencies point inward: `domain` ← `application` ← `infrastructure` / `presentation`.

- **domain/**: pure entities and errors. `Group` is an aggregate: membership, join requests, approval, removal and leaving all go through its methods, which enforce the rules (only the owner approves, the owner can't leave, and so on).
- **application/**: use-case services (`AuthService`, `GroupService`, `ItemService`) that depend only on `Protocol`s in `ports.py` (repositories, password hasher, token service, event publisher). They return read models from `dto.py`.
- **infrastructure/**: adapters. There are two persistence backends:
  - Firestore (`firestore_repositories.py`), used in production.
  - Local JSON (`json_database.py` + `json_repositories.py`): in-memory, with atomic writes, rollback and a thread lock.

  Both serialize through `mappers.py`. `event_broker.py` is an in-memory SSE pub/sub, so it only works with a single process.
- **container.py**: the composition root, and the only place that knows concrete classes. It picks Firestore when `FIREBASE_CREDENTIALS` is set and local JSON otherwise.
- **factory.py**: `create_app(settings)` builds the container, registers error handlers, adds security headers (strict CSP: no inline scripts or styles) and mounts the `/api` routers plus the static `presentation/web` directory.
- **presentation/api/**: routes and Pydantic schemas. `errors.py` maps domain exceptions to HTTP codes (`NotFoundError`→404, `PermissionDeniedError`→403, `ConflictError`→409, `ValidationError`→422, `AuthenticationError`→401). Raise domain errors from services. Don't raise `HTTPException`.

Conventions that span layers:
- **Privacy:** a non-member accessing a group gets 404, not 403, so the group's existence isn't revealed. Pending join requests are visible only to the owner.
- **Adding a field to an entity** touches `domain/entities.py`, `persistence/mappers.py`, `application/dto.py`, `api/schemas.py`, the routes, and usually the JS views.
- **Frontend XSS rule:** user text is inserted only via `textContent`, using the `h()` helper in `js/dom.js`.

### Frontend (`app/presentation/web/`)

- `js/app.js` is a hash router (`ROUTES` table) that handles the session and the SSE live updates.
- `js/api.js` is the fetch wrapper. It handles session/token storage and reports offline data.
- `js/views.js` renders the screens.
- `js/shopping.js` is the offline "at the market" mode. Prices stay in `localStorage` only. Bought-marks are queued and synced to the server when the connection returns.
- `sw.js` caches the app shell and keeps the last API responses (`compras-api` cache, whose name is shared with `api.js`) for offline use. **When adding or renaming a frontend file, update the `SHELL` list, and bump `CACHE` (`compras-vN`) whenever shell assets change.**

## Tests

`tests/conftest.py` parametrizes the `backend` fixture over `["json", "firestore"]`, so service and API tests run against both adapters. Firestore is replaced by `tests/fake_firestore.py`, monkeypatched into `app.container.create_firestore_client`. Any new persistence behavior must work in both adapters and in the fake. Fixtures:
- `services` builds the services with a `RecordingPublisher` for asserting notifications, plus a `.user()` helper.
- `client` is a `TestClient` over `create_app(settings)`.

## Configuration and deploy

Environment variables:
- `FIREBASE_CREDENTIALS`: a path to the service-account JSON or its contents. Empty means `data/db.json`.
- `APP_DATA_DIR`
- `APP_SECRET_KEY`: if unset, one is generated in `data/.secret_key`.
- `APP_TOKEN_TTL_DAYS`

`Settings.from_env()` refuses to start without Firestore when `RENDER` or `APP_REQUIRE_DATABASE` is set, because the disk there is ephemeral.

Deploys run on Render via `render.yaml`, automatically on every push to `main`. The Firebase key goes in as the Secret File `/etc/secrets/firebase.json`. `/api/health` reports which storage backend is active.
