import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from export_cattr_event_log import (
    build_event_rows,
    format_event_timestamp,
    parse_user_roles,
    validate_project_names,
    write_event_log,
)


class CattrEventLogExportTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "project_id": 1,
                "project_name": "ONB-TEST-001",
                "task_name": "Review Documents",
                "interval_id": 14,
                "user_id": 3,
                "user_name": "Test User",
                "start_at": datetime(2026, 11, 9, 14, 0, 0),
                "end_at": datetime(2026, 11, 9, 14, 2, 0),
            }
        ]

    def test_creates_one_row_per_interval_with_end_time_and_role(self):
        events = build_event_rows(
            self.records,
            {3: "HR Manager"},
            ZoneInfo("America/Chicago"),
        )

        self.assertEqual(
            events,
            [
                {
                    "Case_Id": "ONB-TEST-001",
                    "Activity": "Review Documents",
                    "Timestamp": "2026-11-09T14:02:00-06:00",
                    "Role": "HR Manager",
                }
            ],
        )

    def test_rejects_missing_business_role_mapping(self):
        with self.assertRaisesRegex(ValueError, "user IDs: 3"):
            build_event_rows(self.records, {}, ZoneInfo("UTC"))

    def test_rejects_interval_ending_before_start(self):
        record = dict(self.records[0], end_at=datetime(2026, 11, 9, 13, 59, 59))

        with self.assertRaisesRegex(ValueError, "ends before it starts"):
            build_event_rows([record], {3: "HR Manager"}, ZoneInfo("UTC"))

    def test_role_mapping_parser_validates_values_and_duplicate_ids(self):
        self.assertEqual(
            parse_user_roles(["3=HR Manager", "4=IT Staff"]),
            {3: "HR Manager", 4: "IT Staff"},
        )
        with self.assertRaisesRegex(ValueError, "expected USER_ID=ROLE"):
            parse_user_roles(["not-a-mapping"])
        with self.assertRaisesRegex(ValueError, "provided more than once"):
            parse_user_roles(["3=HR", "3=IT"])

    def test_project_names_must_exist_and_be_unique_case_ids(self):
        validate_project_names(self.records, ["ONB-TEST-001"])

        with self.assertRaisesRegex(ValueError, "No active time intervals"):
            validate_project_names(self.records, ["ONB-TEST-002"])

        duplicate = dict(self.records[0], project_id=2)
        with self.assertRaisesRegex(ValueError, "must be unique"):
            validate_project_names(
                self.records + [duplicate],
                ["ONB-TEST-001"],
            )

    def test_formats_timezone_naive_database_datetime_with_offset(self):
        timestamp = format_event_timestamp(
            datetime(2026, 11, 9, 14, 2, 0),
            ZoneInfo("America/Chicago"),
        )

        self.assertEqual(timestamp, "2026-11-09T14:02:00-06:00")

    def test_writes_sequential_numbered_snapshots_without_overwriting(self):
        events = build_event_rows(
            self.records,
            {3: "HR Manager"},
            ZoneInfo("America/Chicago"),
        )

        with TemporaryDirectory() as temp_dir:
            output_base = Path(temp_dir) / "cattr_event_log.csv"
            first = write_event_log(events, output_base)
            second = write_event_log(events, output_base)

            self.assertEqual(first.name, "cattr_event_log_001.csv")
            self.assertEqual(second.name, "cattr_event_log_002.csv")
            self.assertNotEqual(first.read_text(), "")
            self.assertEqual(first.read_text(), second.read_text())

    def test_snapshot_numbering_skips_existing_sequence(self):
        events = build_event_rows(
            self.records,
            {3: "HR Manager"},
            ZoneInfo("America/Chicago"),
        )

        with TemporaryDirectory() as temp_dir:
            output_base = Path(temp_dir) / "events.csv"
            (Path(temp_dir) / "events_001.csv").touch()
            (Path(temp_dir) / "events_003.csv").touch()

            output = write_event_log(events, output_base)

            self.assertEqual(output.name, "events_002.csv")


if __name__ == "__main__":
    unittest.main()
