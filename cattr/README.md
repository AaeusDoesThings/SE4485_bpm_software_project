# Cattr Installation
Cattr is deployed with Docker Compose using the official Cattr server image and a Percona MySQL database.

## Exporting events for process mining

Export or transform Cattr time entries into a CSV with one row per completed
process activity and these columns:

| CSV column | Cattr value |
|---|---|
| `Case_Id` | Stable ID for one process instance, such as one employee's onboarding |
| `Activity` | Cattr task name, with task names consistently representing process steps |
| `Timestamp` | Time-entry end time, when the activity was completed |
| `Role` | The time-entry user's business role, populated from a user-to-role mapping |

Use the same `Case_Id` for all events in one process instance and a different ID
for each instance. A shared project is only a suitable case ID if it represents
exactly one instance. A Cattr username identifies the person, not their business
role, so translate users to roles rather than using usernames in `Role`.

The process-mining app accepts `Case_Id` and normalizes it to `Case_ID` when
uploading or previewing a CSV. Cattr's summary reports do not contain individual
interval timestamps. The exporter below reads Cattr's individual `time_intervals`
records, joins each interval to its task, project, and user, and writes one CSV
event per interval. It does not aggregate durations.

### Export individual Cattr time intervals

Run these commands from the repository root, with the Cattr database running.
Build the one-shot exporter and list the user IDs associated with the selected
test projects:

```bash
docker compose -f cattr/docker-compose.yml --profile tools build event-log-exporter
docker compose -f cattr/docker-compose.yml --profile tools run --rm event-log-exporter \
  --project ONB-TEST-001 --project ONB-TEST-002 --list-users
```

Use the listed Cattr user IDs to map each person to their actual business role
(not Cattr's permission role or username). Export the selected projects by
providing one `--user-role USER_ID=ROLE` option per user:

```bash
docker compose -f cattr/docker-compose.yml --profile tools run --rm event-log-exporter \
  --project ONB-TEST-001 --project ONB-TEST-002 \
  --user-role '3=HR Manager' \
  --stored-timezone America/Chicago \
  --output /exports/cattr_event_log.csv
```

Replace the example user ID and role with the actual mapping. `--stored-timezone`
must match the timezone used to interpret Cattr's timezone-naive MySQL
`DATETIME` values. The exporter attaches that timezone to each `end_at` value
and writes it as an ISO 8601 timestamp with an offset. Confirm the chosen
timezone against Cattr's displayed time before using the log for analysis.

The `--output` value is a filename base. Each run creates a numbered snapshot
without overwriting previous exports: `server/exports/cattr_event_log_001.csv`,
then `_002.csv`, and so on. If a number already exists, the exporter skips it.
Open the printed output path and upload that CSV through the process-mining app.
Export only the intended test projects; each project name is used as a case ID,
and task names should be consistent across cases.

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
