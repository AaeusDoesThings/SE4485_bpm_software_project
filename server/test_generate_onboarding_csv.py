import csv
import tempfile
import unittest
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from generate_onboarding_csv import (
    ACTIVITIES,
    CSV_COLUMNS,
    ROLE_ACTIVITIES,
    ROLE_BY_ACTIVITY,
    generate_event_log,
)


class RoleCatalogTests(unittest.TestCase):
    def test_activity_catalog_assigns_each_activity_to_one_role(self):
        catalog_activities = [
            activity
            for activities in ROLE_ACTIVITIES.values()
            for activity in activities
        ]

        self.assertEqual(len(catalog_activities), len(set(catalog_activities)))
        self.assertEqual(set(catalog_activities), set(ACTIVITIES))
        self.assertEqual(set(ROLE_BY_ACTIVITY), set(ACTIVITIES))

    def test_role_categories_match_the_onboarding_responsibilities(self):
        self.assertEqual(
            set(ROLE_ACTIVITIES["HR Manager"]),
            {
                "Coordinate onboarding plan",
                "Schedule orientation session",
                "Send welcome email",
                "Conduct introduction session",
                "First Week Check-in",
                "Send follow-up email",
                "Collect onboarding feedback",
            },
        )
        self.assertEqual(
            set(ROLE_ACTIVITIES["New Hire"]),
            {
                "Complete onboarding documentation",
                "Resubmit onboarding documentation",
                "Complete Training Module 1",
                "Complete Training Module 2",
            },
        )
        self.assertEqual(
            set(ROLE_ACTIVITIES["IT Staff"]),
            {
                "Prepare laptop and equipment",
                "Create employee accounts",
                "Grant technical access",
                "Resolve technical access issue",
            },
        )


class EventLogTests(unittest.TestCase):
    def test_generation_is_repeatable_and_uses_role_catalog(self):
        first_run = generate_event_log(3, date(2025, 1, 1), 42)
        second_run = generate_event_log(3, date(2025, 1, 1), 42)

        self.assertEqual(first_run, second_run)
        self.assertEqual({event["Case_ID"] for event in first_run}, {
            "EMP00001",
            "EMP00002",
            "EMP00003",
        })
        self.assertTrue(
            all(ROLE_BY_ACTIVITY[event["Activity"]] == event["Role"] for event in first_run)
        )

    def test_generated_cases_have_ordered_parseable_timestamps(self):
        events = generate_event_log(4, date(2025, 1, 1), 42)
        by_case = defaultdict(list)
        for event in events:
            by_case[event["Case_ID"]].append(
                datetime.strptime(event["Timestamp"], "%Y-%m-%d %H:%M:%S")
            )

        for timestamps in by_case.values():
            self.assertEqual(timestamps, sorted(timestamps))

    def test_generation_rejects_zero_or_negative_case_count(self):
        for case_count in (0, -1):
            with self.subTest(case_count=case_count):
                with self.assertRaisesRegex(ValueError, "at least 1"):
                    generate_event_log(case_count, date(2025, 1, 1), 42)

    def test_generated_csv_uses_expected_upload_columns(self):
        events = generate_event_log(2, date(2025, 1, 1), 42)
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "onboarding.csv"
            with output.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(events)

            with output.open(newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                rows = list(reader)

        self.assertEqual(reader.fieldnames, CSV_COLUMNS)
        self.assertEqual(len(rows), len(events))
        self.assertTrue(all(row["Role"] == ROLE_BY_ACTIVITY[row["Activity"]] for row in rows))


if __name__ == "__main__":
    unittest.main()
