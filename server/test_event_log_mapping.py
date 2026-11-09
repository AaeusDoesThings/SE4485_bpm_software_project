import unittest

import pandas as pd

from event_log_mapping import normalize_case_id_column


class CaseIdColumnTests(unittest.TestCase):
    def test_normalizes_cattr_case_id_spelling(self):
        events = pd.DataFrame(
            [{"Case_Id": "EMP001", "Activity": "Review", "Timestamp": "2026-01-01 09:00:00", "Role": "HR"}]
        )

        normalized = normalize_case_id_column(events)

        self.assertIn("Case_ID", normalized.columns)
        self.assertNotIn("Case_Id", normalized.columns)
        self.assertEqual(normalized.iloc[0]["Case_ID"], "EMP001")

    def test_keeps_existing_case_id_column(self):
        events = pd.DataFrame([{"Case_ID": "EMP001"}])

        normalized = normalize_case_id_column(events)

        self.assertIs(normalized, events)
        self.assertIn("Case_ID", normalized.columns)


if __name__ == "__main__":
    unittest.main()
