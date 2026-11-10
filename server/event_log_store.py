import io
import os
from datetime import datetime, timezone
from pathlib import Path

import mysql.connector
import pandas as pd

from event_log_mapping import normalize_case_id_column


EVENT_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS event_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_filename VARCHAR(255) NOT NULL,
    imported_at_utc DATETIME(6) NOT NULL,
    event_count INT UNSIGNED NOT NULL,
    INDEX idx_event_logs_imported_at (imported_at_utc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

EVENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS event_log_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    event_log_id BIGINT UNSIGNED NOT NULL,
    event_order INT UNSIGNED NOT NULL,
    case_id VARCHAR(255) NOT NULL,
    activity VARCHAR(255) NOT NULL,
    timestamp_utc DATETIME(6) NOT NULL,
    timestamp_original VARCHAR(64) NOT NULL,
    role VARCHAR(255) NOT NULL,
    CONSTRAINT fk_event_log_events_log
        FOREIGN KEY (event_log_id) REFERENCES event_logs(id) ON DELETE CASCADE,
    UNIQUE KEY uq_event_log_order (event_log_id, event_order),
    INDEX idx_events_case_timestamp (event_log_id, case_id, timestamp_utc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def connect_to_event_log_store():
    return mysql.connector.connect(
        host=os.environ["BPM_DB_HOST"],
        port=int(os.environ.get("BPM_DB_PORT", "3306")),
        user=os.environ["BPM_DB_USER"],
        password=os.environ["BPM_DB_PASSWORD"],
        database=os.environ["BPM_DB_NAME"],
        connection_timeout=10,
    )


def initialize_event_log_store() -> None:
    connection = connect_to_event_log_store()
    try:
        with connection.cursor() as cursor:
            cursor.execute(EVENT_LOG_SCHEMA)
            cursor.execute(EVENT_SCHEMA)
        connection.commit()
    finally:
        connection.close()


def parse_event_log_csv(contents: bytes) -> list[dict]:
    try:
        decoded = contents.decode("utf-8-sig")
        dataframe = pd.read_csv(io.StringIO(decoded))
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError(f"Unable to read the uploaded CSV: {error}") from error

    dataframe = normalize_case_id_column(dataframe)
    required_columns = {"Case_ID", "Activity", "Timestamp", "Role"}
    missing_columns = sorted(required_columns - set(dataframe.columns))
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")
    if dataframe.empty:
        raise ValueError("CSV contains no event rows")

    rows = []
    for row_number, row in enumerate(
        dataframe[["Case_ID", "Activity", "Timestamp", "Role"]].to_dict(orient="records"),
        start=2,
    ):
        case_id, activity, timestamp_text, role = (
            "" if pd.isna(row[column]) else str(row[column]).strip()
            for column in ("Case_ID", "Activity", "Timestamp", "Role")
        )
        if not case_id or not activity or not timestamp_text or not role:
            raise ValueError(f"CSV row {row_number} has an empty required value")

        try:
            parsed_timestamp = pd.to_datetime(timestamp_text, utc=True, errors="raise")
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"CSV row {row_number} has an invalid Timestamp: {timestamp_text!r}"
            ) from error

        rows.append(
            {
                "event_order": row_number - 1,
                "case_id": case_id,
                "activity": activity,
                "timestamp_utc": parsed_timestamp.to_pydatetime()
                .astimezone(timezone.utc)
                .replace(tzinfo=None),
                "timestamp_original": timestamp_text,
                "role": role,
            }
        )

    return rows


def store_event_log(connection, source_filename: str, events: list[dict]) -> int:
    if not events:
        raise ValueError("Cannot store an event log with no events")

    safe_filename = Path(source_filename).name[:255] or "uploaded.csv"
    connection.start_transaction()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO event_logs (name, source_filename, imported_at_utc, event_count)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    safe_filename,
                    safe_filename,
                    datetime.now(timezone.utc).replace(tzinfo=None),
                    len(events),
                ),
            )
            event_log_id = cursor.lastrowid
            cursor.executemany(
                """
                INSERT INTO event_log_events
                    (event_log_id, event_order, case_id, activity,
                     timestamp_utc, timestamp_original, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        event_log_id,
                        event["event_order"],
                        event["case_id"],
                        event["activity"],
                        event["timestamp_utc"],
                        event["timestamp_original"],
                        event["role"],
                    )
                    for event in events
                ],
            )
        connection.commit()
        return int(event_log_id)
    except mysql.connector.Error:
        connection.rollback()
        raise


def list_event_logs(connection) -> list[dict]:
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            """
            SELECT id, name, source_filename, imported_at_utc, event_count
            FROM event_logs
            ORDER BY imported_at_utc DESC, id DESC
            """
        )
        return cursor.fetchall()


def get_event_log_events(connection, event_log_id: int) -> list[dict] | None:
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            "SELECT id, name, source_filename, event_count FROM event_logs WHERE id = %s",
            (event_log_id,),
        )
        log_record = cursor.fetchone()
        if log_record is None:
            return None

        cursor.execute(
            """
            SELECT case_id AS Case_ID, activity AS Activity,
                   timestamp_original AS Timestamp, role AS Role
            FROM event_log_events
            WHERE event_log_id = %s
            ORDER BY event_order
            """,
            (event_log_id,),
        )
        return cursor.fetchall()


def get_event_log_dataframe(connection, event_log_id: int) -> pd.DataFrame | None:
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            """
            SELECT case_id AS Case_ID, activity AS Activity,
                   timestamp_utc AS Timestamp, role AS Role
            FROM event_log_events
            WHERE event_log_id = %s
            ORDER BY event_order
            """,
            (event_log_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return pd.DataFrame(rows)
