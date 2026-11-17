# Agent Instructions

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
pip install -r requirements.txt
python run.sh     # uvicorn at port 8000, root-path /api/photoparser
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