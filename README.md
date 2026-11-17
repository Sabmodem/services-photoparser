# PhotoParser

A photo parsing service with a Vue 3 frontend and FastAPI backend.

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL database
- Redis server

### Running the API

```bash
cd photoparser-api
pip install -r requirements.txt
python run.sh
```

The API will run at `http://localhost:8000/api/photoparser`.

### Running the UI

```bash
cd photoparser-ui
npm install
npm run dev
```

The UI will run at `http://localhost:3000/ui/photoparser/`.

## Architecture

- **Frontend**: Vue 3 + Vuetify 3 + Vite
- **Backend**: FastAPI + SQLAlchemy async + asyncpg
- **Queue**: Redis + RQ for background search tasks
- **Database**: PostgreSQL

## API Endpoints

- `POST /api/photoparser/search_query/` - Create a new search query
- `GET /api/photoparser/search_query/` - List search queries
- `GET /api/photoparser/search_query/{id}` - Get a specific search query
- `POST /api/photoparser/search_query/{id}/search_results/` - Add search results
- `POST /api/photoparser/search_query/{id}/status` - Update search query status
- `GET /api/photoparser/search_results/` - List search results
- `GET /api/photoparser/search_results/{id}` - Get a specific search result

## Development

### UI
- Pages are auto-routed from `src/pages/*.vue`
- Vuetify components auto-import
- ESLint: `npm run lint`

### API
- CRUD operations in `crud.py`
- Models in `models.py`
- Schemas in `schemas.py`
- Background search tasks in `search.py`


### TODO:
- docker-compose.yaml
- ci pipeline for both containers
- alembic
