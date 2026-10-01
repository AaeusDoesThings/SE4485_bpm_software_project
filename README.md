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
git clone https://github.com/AaeusDoesThings/SE4485_bpm_software_project.git bpm_software_project
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

### Pull base images manually (optional)

Docker pulls these base images automatically during the build if they are not already available locally. To pull them manually:

```bash
docker pull python:3.11-slim
docker pull node:20
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


## Update an Existing Clone

If you already cloned an older version, you do not need to clone it again.

### Open the existing project folder

```bash
cd path/to/your/existing-project
```

### Check for local changes

```bash
git status
```

If you have uncommitted changes, save them before updating:

```bash
git add .
git commit -m "Save local changes before update"
```

### Update the repository URL

If the existing clone already has an `origin` remote, update it with:

```bash
git remote set-url origin https://github.com/AaeusDoesThings/SE4485_bpm_software_project.git
```

If it does not have an `origin` remote, add one instead:

```bash
git remote add origin https://github.com/AaeusDoesThings/SE4485_bpm_software_project.git
```

Verify the remote:

```bash
git remote -v
```

### Download the latest version

```bash
git fetch origin
git pull --rebase origin main
```

If Git reports conflicts, resolve them in the listed files, then run:

```bash
git add .
git commit -m "Resolve update conflicts"
```

### Rebuild and start the application

Run this from the project root, where `docker-compose.yml` is located:

```bash
docker compose up --build
```
