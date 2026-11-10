import unittest
from datetime import datetime

import mysql.connector

from event_log_store import parse_event_log_csv, store_event_log


class EventLogCsvParsingTests(unittest.TestCase):
    def test_parses_case_id_spelling_and_keeps_original_offset(self):
        events = parse_event_log_csv(
            b"Case_Id,Activity,Timestamp,Role\n"
            b"CASE-1,Review,2026-11-09T14:00:00-06:00,HR Manager\n"
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["case_id"], "CASE-1")
        self.assertEqual(events[0]["activity"], "Review")
        self.assertEqual(events[0]["timestamp_original"], "2026-11-09T14:00:00-06:00")
        self.assertEqual(
            events[0]["timestamp_utc"],
            datetime(2026, 11, 9, 20, 0, 0),
        )

    def test_rejects_missing_columns_empty_values_and_invalid_timestamps(self):
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            parse_event_log_csv(b"Case_Id,Activity\nCASE-1,Review\n")
        with self.assertRaisesRegex(ValueError, "empty required value"):
            parse_event_log_csv(
                b"Case_Id,Activity,Timestamp,Role\nCASE-1,,2026-11-09T14:00:00Z,HR\n"
            )
        with self.assertRaisesRegex(ValueError, "invalid Timestamp"):
            parse_event_log_csv(
                b"Case_Id,Activity,Timestamp,Role\nCASE-1,Review,not-a-time,HR\n"
            )

    def test_rejects_empty_event_log(self):
        with self.assertRaisesRegex(ValueError, "no event rows"):
            parse_event_log_csv(b"Case_Id,Activity,Timestamp,Role\n")


class EventLogStorageTests(unittest.TestCase):
    def test_stores_import_and_events_in_one_transaction(self):
        connection = FakeConnection()
        events = parse_event_log_csv(
            b"Case_Id,Activity,Timestamp,Role\n"
            b"CASE-1,Review,2026-11-09T14:00:00-06:00,HR Manager\n"
        )

        event_log_id = store_event_log(connection, "../../pilot.csv", events)

        self.assertEqual(event_log_id, 27)
        self.assertTrue(connection.transaction_started)
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        metadata_insert = connection.cursor_instance.executed[0]
        self.assertEqual(metadata_insert[1][0], "pilot.csv")
        self.assertEqual(metadata_insert[1][1], "pilot.csv")
        event_insert = connection.cursor_instance.executed_many[0]
        self.assertEqual(event_insert[0][0:4], (27, 1, "CASE-1", "Review"))
        self.assertEqual(event_insert[0][6], "HR Manager")

    def test_rolls_back_storage_errors(self):
        connection = FakeConnection(fail_on_insert=True)

        with self.assertRaisesRegex(mysql.connector.Error, "insert failed"):
            store_event_log(connection, "pilot.csv", [{"event_order": 1}])

        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.lastrowid = 27
        self.executed = []
        self.executed_many = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, values):
        self.executed.append((query, values))
        if self.connection.fail_on_insert:
            raise mysql.connector.Error("insert failed")

    def executemany(self, query, values):
        self.executed_many.append(values)


class FakeConnection:
    def __init__(self, fail_on_insert=False):
        self.fail_on_insert = fail_on_insert
        self.cursor_instance = FakeCursor(self)
        self.transaction_started = False
        self.committed = False
        self.rolled_back = False

    def start_transaction(self):
        self.transaction_started = True

    def cursor(self, **kwargs):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


if __name__ == "__main__":
    unittest.main()
