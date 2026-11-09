import argparse
import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROLE_ACTIVITIES = {
    "HR Manager": [
        "Coordinate onboarding plan",
        "Schedule orientation session",
        "Send welcome email",
        "Conduct introduction session",
        "First Week Check-in",
        "Send follow-up email",
        "Collect onboarding feedback",
    ],
    "New Hire": [
        "Complete onboarding documentation",
        "Resubmit onboarding documentation",
        "Complete Training Module 1",
        "Complete Training Module 2",
    ],
    "IT Staff": [
        "Prepare laptop and equipment",
        "Create employee accounts",
        "Grant technical access",
        "Resolve technical access issue",
    ],
}

ROLE_BY_ACTIVITY = {
    activity: role
    for role, activities in ROLE_ACTIVITIES.items()
    for activity in activities
}
ACTIVITIES = list(ROLE_BY_ACTIVITY)

CSV_COLUMNS = [
    "Case_ID",
    "Activity",
    "Timestamp",
    "CO2_Impact",
    "Activity_Cost",
    "Role",
]


def build_case(case_id: str, start: datetime, rng: random.Random) -> list[dict[str, str]]:
    activities = [
        "Coordinate onboarding plan",
        "Schedule orientation session",
        "Send welcome email",
        "Complete onboarding documentation",
    ]

    if rng.random() < 0.25:
        activities.append("Resubmit onboarding documentation")

    activities.extend(
        [
            "Conduct introduction session",
            "Prepare laptop and equipment",
            "Create employee accounts",
            "Grant technical access",
        ]
    )

    if rng.random() < 0.2:
        activities.append("Resolve technical access issue")

    activities.extend(
        [
            "First Week Check-in",
            "Complete Training Module 1",
            "Complete Training Module 2",
            "Send follow-up email",
            "Collect onboarding feedback",
        ]
    )

    events = []
    timestamp = start
    for activity in activities:
        events.append(
            {
                "Case_ID": case_id,
                "Activity": activity,
                "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "CO2_Impact": f"{rng.uniform(0.1, 2.0):.2f}",
                "Activity_Cost": f"{rng.uniform(50.0, 500.0):.2f}",
                "Role": ROLE_BY_ACTIVITY[activity],
            }
        )
        timestamp += timedelta(days=rng.randint(1, 5), hours=rng.randint(0, 8))

    return events


def generate_event_log(case_count: int, start_date: date, seed: int) -> list[dict[str, str]]:
    if case_count < 1:
        raise ValueError("case_count must be at least 1")

    rng = random.Random(seed)
    events = []
    for case_number in range(1, case_count + 1):
        case_start = datetime.combine(start_date, time(9, 0)) + timedelta(
            days=(case_number - 1) * rng.randint(2, 7)
        )
        events.extend(build_case(f"EMP{case_number:05d}", case_start, rng))
    return events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic onboarding event-log CSV with predefined activity roles."
    )
    parser.add_argument("--cases", type=int, default=10, help="Number of made-up hires (default: 10)")
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date.today(),
        help="First case start date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatable output")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("examples/synthetic_onboarding.csv"),
        help="Output CSV path (default: examples/synthetic_onboarding.csv)",
    )
    args = parser.parse_args()

    events = generate_event_log(args.cases, args.start_date, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(events)

    print(f"Wrote {len(events)} synthetic events for {args.cases} cases to {args.output}")


if __name__ == "__main__":
    main()
