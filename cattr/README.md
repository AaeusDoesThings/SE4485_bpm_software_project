# Cattr Installation
Cattr is deployed with Docker Compose using the official Cattr server image and a Percona MySQL database.

## Prerequisites
Install:
- Docker Engine
- Docker Compose v2

Verify the installation:
```bash
docker --version
docker compose version
```

## Installation
From the repository root, enter the Cattr directory:

```bash
cd cattr
```

## Create a `.env` file in this directory. Use this template. The reason why it is 8002 is because I have 8000 and 8001 in used. Find out what port it is not in use by running netstat -ano | findstr :{cattr_port_#}
```env
APP_URL=http://localhost:8002 
APP_KEY=base64:replace-with-a-unique-application-key

DB_PASSWORD=replace-with-a-secure-database-password
DB_ROOT_PASSWORD=replace-with-a-secure-root-password

APP_ADMIN_EMAIL=admin@example.com
APP_ADMIN_PASSWORD=replace-with-a-secure-admin-password
APP_ADMIN_NAME=Admin
```

Do not commit `.env` to version control. Use unique passwords for production deployments.

Start Cattr:

```bash
docker compose up -d
```

The first startup downloads the application and database images and may take a few minutes.
Open Cattr in your browser at [http://localhost:8002](http://localhost:8002).
Sign in with the administrator account configured through `APP_ADMIN_EMAIL` and `APP_ADMIN_PASSWORD`.

## View Logs
View logs for all services:

```bash
docker compose logs -f
```

View application logs:

```bash
docker compose logs -f app
```

View database logs:

```bash
docker compose logs -f db
```

## Stop Cattr
Stop the containers while keeping stored data:

```bash
docker compose down
```

Start them again later:

```bash
docker compose up -d
```

## Data Storage
Docker volumes persist application and database data:

- `backend_storage` stores Cattr application data.
- `database` stores MySQL data.

To remove the containers and all persisted data:

```bash
docker compose down -v
```

Warning: `docker compose down -v` permanently deletes the Cattr database and application storage.

## Updating Cattr
Pull the latest application image and restart the services:
```bash
docker compose pull
docker compose up -d
```

Check the service status:
```bash
docker compose ps
```

## Troubleshooting
If the application cannot connect to the database, check the service status and database logs:
```bash
docker compose ps
docker compose logs db
```

To recreate the application container:

```bash
docker compose up -d --force-recreate app
```

