# Business Process Mining Software

This application consists of:

- FastAPI backend for process mining
- Next.js frontend

## Run with Docker

### Prerequisites

Install Docker and Docker Compose. Verify the installation with:

```bash
docker --version
docker compose version
```

### Clone the repository

```bash
git clone <repository-url>
cd bpm_software_project
```

### Build and start the application

The Compose file builds both services locally from their Dockerfiles:

```bash
docker compose up --build
```

Open the application at:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

To run the application in the background:

```bash
docker compose up --build -d
```

### Pull base images

The services are built locally rather than pulled from a container registry. To pull the base images used by the Dockerfiles:

```bash
docker pull python:3.11-slim
docker pull node:20
```

Then build and start the application:

```bash
docker compose up --build
```

### View logs

```bash
docker compose logs -f
```

To view logs for one service:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### Stop the application

```bash
docker compose down
```

To also remove orphaned containers:

```bash
docker compose down --remove-orphans
```

### Rebuild after code changes

```bash
docker compose up --build
```

## Run locally without Docker

### Backend

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fastapi dev
```

The backend runs at http://localhost:8000.

### Frontend

In a separate terminal:

```bash
cd client
npm install
npm run dev
```

The frontend runs at http://localhost:3000.
