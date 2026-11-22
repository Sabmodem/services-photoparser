# Agent Instructions

## Environment Setup (Important)

This project uses a `flake.nix` at the root. **Always activate it before running commands** — it sets up `LD_LIBRARY_PATH` for compiled packages (PyTorch, etc.) and activates the `.venv`:

```bash
cd /home/sabmodem/projects/services-photoparser
nix develop          # default shell (includes FHS libs + .venv)
nix develop .#migrations  # shell with alembic for DB migrations
nix develop -c <command>   # run a single command in the shell
```

Without `nix develop`, `alembic`, `uv`, and other tools won't be found, and compiled packages may fail with library errors.

## Project Structure

Monorepo with two packages:
- `photoparser-ui` - Vue 3 + Vuetify 3 frontend (Vite)
- `photoparser-api` - FastAPI + SQLAlchemy async backend

## Commands

### UI
```bash
cd photoparser-ui
npm install
npm run dev       # dev server at localhost:3000
npm run build     # production build
npm run lint      # eslint --fix
```

### API
```bash
cd photoparser-api
uv sync          # install dependencies (uses pyproject.toml + uv.lock)
uvicorn main:app --host 0.0.0.0 --port 8000 --root-path /api/photoparser
```

## Architecture Notes

- UI uses `unplugin-vue-router` for automatic page routes from `src/pages/*.vue`
- UI uses `unplugin-vue-components` for auto-imported Vuetify components
- API uses Redis + RQ for background job queue (search tasks)
- API connects to PostgreSQL via `database.py` (asyncpg)
- UI base path is `/ui/photoparser/` (configured in `vite.config.mjs`)

## Conventions

- No root-level lint/test scripts - commands are package-specific
- Vue 3 `<script setup>` SFCs in `src/pages/*.vue`
- API CRUD in `crud.py`, models in `models.py`, schemas in `schemas.py`