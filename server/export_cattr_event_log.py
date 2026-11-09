import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CSV_COLUMNS = ["Case_Id", "Activity", "Timestamp", "Role"]


def parse_user_roles(values: list[str]) -> dict[int, str]:
    roles: dict[int, str] = {}
    for value in values:
        user_id_text, separator, role = value.partition("=")
        if not separator or not user_id_text.isdigit() or not role.strip():
            raise ValueError(f"Invalid user-role mapping: {value!r}; expected USER_ID=ROLE")
        user_id = int(user_id_text)
        if user_id in roles:
            raise ValueError(f"Role mapping for user ID {user_id} was provided more than once")
        roles[user_id] = role.strip()
    return roles


def format_event_timestamp(value: datetime, timezone: ZoneInfo) -> str:
    if value.tzinfo is not None:
        raise ValueError("Expected Cattr's timezone-naive MySQL DATETIME value")
    return value.replace(tzinfo=timezone).isoformat(timespec="seconds")


def build_event_rows(
    records: list[dict],
    user_roles: dict[int, str],
    timezone: ZoneInfo,
) -> list[dict[str, str]]:
    missing_roles = sorted({record["user_id"] for record in records} - user_roles.keys())
    if missing_roles:
        ids = ", ".join(str(user_id) for user_id in missing_roles)
        raise ValueError(f"Missing business-role mappings for Cattr user IDs: {ids}")

    events = []
    for record in records:
        if not record["project_name"] or not record["task_name"]:
            raise ValueError("Cattr interval is missing its project name or task name")
        if record["end_at"] < record["start_at"]:
            raise ValueError(f"Cattr interval {record['interval_id']} ends before it starts")

        events.append(
            {
                "Case_Id": record["project_name"],
                "Activity": record["task_name"],
                "Timestamp": format_event_timestamp(record["end_at"], timezone),
                "Role": user_roles[record["user_id"]],
            }
        )
    return events


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export individual Cattr time intervals as a BPM event-log CSV."
    )
    parser.add_argument(
        "--project",
        action="append",
        required=True,
        help="Exact Cattr project name to export; repeat to select multiple projects.",
    )
    parser.add_argument(
        "--list-users",
        action="store_true",
        help="List Cattr user IDs with intervals in the selected projects, then exit.",
    )
    parser.add_argument(
        "--user-role",
        action="append",
        default=[],
        metavar="USER_ID=ROLE",
        help="Map a Cattr user ID to their business role; repeat for each user.",
    )
    parser.add_argument(
        "--stored-timezone",
        help=(
            "IANA timezone to attach to Cattr's timezone-naive interval end_at values, "
            "for example America/Chicago."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/exports/cattr_event_log.csv"),
        help="Output CSV path (default: /exports/cattr_event_log.csv).",
    )
    return parser


def query_records(connection, project_names: list[str]) -> list[dict]:
    placeholders = ", ".join(["%s"] * len(project_names))
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            f"""
            SELECT p.id AS project_id, p.name AS project_name,
                   t.task_name, ti.id AS interval_id, ti.user_id,
                   u.full_name AS user_name, ti.start_at, ti.end_at
            FROM time_intervals AS ti
            JOIN tasks AS t ON t.id = ti.task_id
            JOIN projects AS p ON p.id = t.project_id
            JOIN users AS u ON u.id = ti.user_id
            WHERE ti.deleted_at IS NULL
              AND t.deleted_at IS NULL
              AND p.deleted_at IS NULL
              AND u.deleted_at IS NULL
              AND p.name IN ({placeholders})
            ORDER BY p.id, ti.end_at, ti.id
            """,
            project_names,
        )
        return cursor.fetchall()


def list_project_users(connection, project_names: list[str]) -> list[dict]:
    placeholders = ", ".join(["%s"] * len(project_names))
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            f"""
            SELECT DISTINCT u.id AS user_id, u.full_name AS user_name
            FROM time_intervals AS ti
            JOIN tasks AS t ON t.id = ti.task_id
            JOIN projects AS p ON p.id = t.project_id
            JOIN users AS u ON u.id = ti.user_id
            WHERE ti.deleted_at IS NULL
              AND t.deleted_at IS NULL
              AND p.deleted_at IS NULL
              AND u.deleted_at IS NULL
              AND p.name IN ({placeholders})
            ORDER BY u.id
            """,
            project_names,
        )
        return cursor.fetchall()


def validate_project_names(records: list[dict], requested_names: list[str]) -> None:
    matched_names = {record["project_name"] for record in records}
    missing_names = sorted(set(requested_names) - matched_names)
    if missing_names:
        raise ValueError(
            "No active time intervals found for selected project(s): "
            + ", ".join(missing_names)
        )

    project_ids_by_name: dict[str, set[int]] = {}
    for record in records:
        project_ids_by_name.setdefault(record["project_name"], set()).add(record["project_id"])
    duplicates = sorted(name for name, ids in project_ids_by_name.items() if len(ids) > 1)
    if duplicates:
        raise ValueError(
            "Project names must be unique to serve as Case_Id; duplicate name(s): "
            + ", ".join(duplicates)
        )


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    project_names = list(dict.fromkeys(args.project))

    try:
        import mysql.connector
    except ImportError:
        parser.error("mysql-connector-python is required to connect to the Cattr database")

    connection = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_DATABASE"],
    )
    try:
        if args.list_users:
            users = list_project_users(connection, project_names)
            if not users:
                raise ValueError("No active time intervals found for the selected project(s)")
            writer = csv.writer(sys.stdout)
            writer.writerow(["Cattr user ID", "User name"])
            writer.writerows((user["user_id"], user["user_name"]) for user in users)
            return 0

        if not args.stored_timezone:
            parser.error("--stored-timezone is required when exporting events")
        try:
            timezone = ZoneInfo(args.stored_timezone)
        except ZoneInfoNotFoundError:
            parser.error(f"Unknown IANA timezone: {args.stored_timezone}")

        try:
            user_roles = parse_user_roles(args.user_role)
        except ValueError as error:
            parser.error(str(error))

        records = query_records(connection, project_names)
        validate_project_names(records, project_names)
        events = build_event_rows(records, user_roles, timezone)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(events)
    finally:
        connection.close()

    print(f"Wrote {len(events)} individual time intervals to {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Export failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
