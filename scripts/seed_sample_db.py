"""Build the sample Observatory Booking database used for testing.

Replaces the app's default local database (repo-root
observatory_booking.db, the same file/path `get_database_url()` falls back
to) with a freshly seeded one containing:

- A handful of easy-to-remember named accounts (superadmin, admin, two
  regular users, one blocked user) for manual/demo testing.
- Thousands of bulk-inserted synthetic users/events/bookings so the database
  resembles a real, long-lived deployment - this is what surfaces N+1
  queries, missing indexes, and unbounded-loop inefficiencies that a
  handful of rows never would.

Bulk data uses bulk_insert_mappings rather than the ORM's per-row service
layer: bcrypt alone is deliberately ~100-300ms per call and would take
minutes for thousands of users, so the bulk users all share one precomputed
hash instead of hashing individually.

For local testing only. Not portable to another machine's .env: emails are
encrypted with this environment's AES keys.

Run with:

    uv run python scripts/seed_sample_db.py [n_users] [n_events] [bookings_per_event_avg]

Defaults produce ~5000 users, 365 events, ~30 bookings/event on average.
"""

import os
import random
import sys
from datetime import datetime, time as dtime, timedelta, timezone

SAMPLE_DB_FILENAME = "observatory_booking.db"
CREDENTIALS_FILENAME = "SAMPLE_DATA_CREDENTIALS.md"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DB_PATH = os.path.join(REPO_ROOT, SAMPLE_DB_FILENAME)
CREDENTIALS_PATH = os.path.join(REPO_ROOT, CREDENTIALS_FILENAME)

# Running this file directly (`python scripts/seed_sample_db.py`, as
# documented above) does not put the repo root on sys.path, so `import
# app.*` below would fail with ModuleNotFoundError - add it explicitly.
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

if os.path.exists(SAMPLE_DB_PATH):
    os.remove(SAMPLE_DB_PATH)

# Must be set before the first `import app.*`.
os.environ["DATABASE_URL"] = f"sqlite:///{SAMPLE_DB_PATH}"
os.environ["DEFAULT_ADMIN_EMAIL"] = "admin@example.com"
os.environ["DEFAULT_ADMIN_PASSWORD"] = "admin"
os.environ["ENV"] = "production"  # avoid SQLAlchemy echo=True spam for bulk inserts

from app.booking_system import (
    BookingSystem,
)  # noqa: E402  pylint: disable=wrong-import-position
from app.data_transfer_objects import (
    EventData,
)  # noqa: E402  pylint: disable=wrong-import-position
from app.models import (
    User,
    Event,
    Booking,
)  # noqa: E402  pylint: disable=wrong-import-position
from app.utils import encrypt_data  # noqa: E402  pylint: disable=wrong-import-position

N_BULK_USERS = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
N_BULK_EVENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 365
BOOKINGS_PER_EVENT_AVG = int(sys.argv[3]) if len(sys.argv) > 3 else 30

random.seed(42)  # reproducible fixture

# (email local-part, full name, password) - password intentionally == local-part.
NAMED_USERS = [
    ("alice", "Alice Johnson", "alice"),
    ("bob", "Bob Smith", "bob"),
    ("carol", "Carol Davis", "carol"),  # promoted to Admin below
    ("dave", "Dave Wilson", "dave"),  # blocked below
]

NAMED_EVENTS = [
    # (days_ahead, title, description, opening, closing, max_bookings)
    (
        3,
        "Meteor Shower Watch",
        "Observe the Perseid meteor shower with our main telescope array.",
        dtime(20, 0),
        dtime(23, 0),
        2,
    ),
    (
        7,
        "Lunar Eclipse Viewing",
        "Full lunar eclipse viewing session, weather permitting.",
        dtime(21, 0),
        dtime(23, 30),
        5,
    ),
    (
        14,
        "Planetary Alignment",
        "A rare alignment of Jupiter, Saturn, and Mars.",
        dtime(19, 0),
        dtime(22, 0),
        10,
    ),
]


def seed_named_users(system):
    """Create the small set of friendly, memorable accounts."""
    with system as db:
        for _, name, password in NAMED_USERS:
            email = f"{_}@example.com"
            db.add(User(name=name, email=email, password=password))
        db.commit()
        ids = {
            f"{local_part}@example.com": db.query(User)
            .filter(User.name == name)
            .first()
            .id
            for local_part, name, _ in NAMED_USERS
        }

    with system as db:
        carol = db.query(User).filter(User.id == ids["carol@example.com"]).first()
        carol.role = "Admin"
        carol.admin_rank = None
        dave = db.query(User).filter(User.id == ids["dave@example.com"]).first()
        dave.blocked = True
        db.commit()

    return ids


def seed_named_events(system):
    """Create the 3 friendly events via the real AdminService validation path."""
    event_ids = []
    today = datetime.now(timezone.utc).date()
    for days_ahead, title, description, opening, closing, max_bookings in NAMED_EVENTS:
        event = EventData(
            event_title=title,
            event_description=description,
            event_date=datetime.combine(
                today + timedelta(days=days_ahead), datetime.min.time()
            ),
            opening_time=opening,
            closing_time=closing,
            max_bookings=max_bookings,
        )
        print(system.confirm_event(event))
    with system as db:
        event_ids = [
            row.id
            for row in db.query(Event.id)
            .filter(Event.title.in_(title for _, title, *_ in NAMED_EVENTS))
            .order_by(Event.start_time)
            .all()
        ]
    return event_ids


def seed_named_bookings(system, user_ids, named_event_ids):
    """Book alice/bob into the named events for an easy, predictable demo."""
    meteor_event, eclipse_event, _alignment_event = named_event_ids
    # Fills the meteor shower event (max_bookings=2).
    print(system.book_event(user_ids["alice@example.com"], meteor_event))
    print(system.book_event(user_ids["bob@example.com"], meteor_event))
    # One booking on the lunar eclipse event. Planetary alignment stays empty.
    print(system.book_event(user_ids["alice@example.com"], eclipse_event))


def build_bulk_users():
    """Bulk-insert N_BULK_USERS rows, reusing one bcrypt hash for speed."""
    shared_hash = User(
        name="__seed_tmp__", email="__seed_tmp__@example.com", password="Password123"
    ).password_hash
    return [
        {
            "name": f"Test User {i:06d}",
            "email_encrypted": encrypt_data(f"user{i:06d}@example.com"),
            "password_hash": shared_hash,
            "role": "User",
            "blocked": i % 500 == 0,  # a sprinkling of blocked accounts
            "admin_rank": None,
        }
        for i in range(1, N_BULK_USERS + 1)
    ]


def build_bulk_events():
    """Bulk-insert N_BULK_EVENTS rows spread across the next N_BULK_EVENTS days.

    Bypasses AdminService.confirm_event's business rules (one event per day,
    weather lookups) on purpose - this is raw fixture data for load testing,
    not a validated business workflow. Starts at day+15 to stay clear of the
    named events above (days 3, 7, 14).
    """
    now = datetime.now(timezone.utc)
    mappings = []
    for i in range(N_BULK_EVENTS):
        start = now + timedelta(days=i + 15, hours=random.randint(-2, 2))
        end = start + timedelta(hours=random.choice([2, 3, 4]))
        mappings.append(
            {
                "title": f"Stress Test Event {i:04d}"[:30],
                "description": f"Synthetic load-test event #{i}.",
                "start_time": start.replace(tzinfo=None),
                "end_time": end.replace(tzinfo=None),
                "available": True,
                "weather_rating": round(random.uniform(0, 100), 1),
                "max_bookings": random.choice([2, 5, 10, 20, 30, 50]),
                "weather_warning": random.random() < 0.1,
                "weather_forecast": True,
            }
        )
    return mappings


def build_bulk_bookings(system, user_ids, events_with_max, existing_pairs):
    """Bulk-insert bookings, respecting the (user_id, event_id) unique pair rule."""
    mappings = []
    seen_pairs = set(existing_pairs)
    with system as db:
        for event_id, max_bookings in events_with_max:
            target = min(
                max_bookings,
                max(
                    0,
                    int(
                        random.gauss(BOOKINGS_PER_EVENT_AVG, BOOKINGS_PER_EVENT_AVG / 3)
                    ),
                ),
            )
            chosen_users = random.sample(user_ids, k=min(target, len(user_ids)))
            for user_id in chosen_users:
                pair = (user_id, event_id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                mappings.append(
                    {"user_id": user_id, "event_id": event_id, "status": "confirmed"}
                )
        db.bulk_insert_mappings(Booking, mappings)
        db.commit()
        print(f"Inserted {len(mappings)} bulk bookings.")


def main():  # pylint: disable=too-many-locals
    """Seed the sample database end-to-end and write the credentials file."""
    system = BookingSystem()

    named_user_ids = seed_named_users(system)
    named_event_ids = seed_named_events(system)
    seed_named_bookings(system, named_user_ids, named_event_ids)

    with system as db:
        db.bulk_insert_mappings(User, build_bulk_users())
        db.commit()
        bulk_user_ids = [
            row.id
            for row in db.query(User.id).filter(User.name.like("Test User %")).all()
        ]
    print(f"Inserted {len(bulk_user_ids)} bulk users.")

    with system as db:
        db.bulk_insert_mappings(Event, build_bulk_events())
        db.commit()
        bulk_events_with_max = [
            (row.id, row.max_bookings)
            for row in db.query(Event.id, Event.max_bookings)
            .filter(Event.title.like("Stress Test Event %"))
            .all()
        ]
    print(f"Inserted {len(bulk_events_with_max)} bulk events.")

    existing_pairs = {
        (named_user_ids["alice@example.com"], named_event_ids[0]),
        (named_user_ids["bob@example.com"], named_event_ids[0]),
        (named_user_ids["alice@example.com"], named_event_ids[1]),
    }
    build_bulk_bookings(system, bulk_user_ids, bulk_events_with_max, existing_pairs)

    system.shutdown()

    total_users = len(NAMED_USERS) + len(bulk_user_ids)
    total_events = len(NAMED_EVENTS) + len(bulk_events_with_max)

    credentials_doc = f"""# Sample Data Credentials

Generated by `scripts/seed_sample_db.py` against `{SAMPLE_DB_FILENAME}`, replacing
the app's default local database. For local testing only. Do not use these
accounts in production, and do not commit this file (repo root, filename
starts with "sample", already gitignored) or the database (`*.db`, also
gitignored).

This database mixes a few friendly named accounts for manual testing with
{len(bulk_user_ids)} bulk-generated users, {len(bulk_events_with_max)} bulk-generated
events, and their bookings, so it resembles a real, long-lived deployment
({total_users} users, {total_events} events total).

Emails are encrypted at rest using this environment's AES keys (.env). This
database is only usable with those same keys - it is not portable to another
machine's .env unless the keys are copied over too.

## Named logins (for manual/demo testing)

All passwords are intentionally simple (matching the email local-part).

| Role       | Email              | Password | Notes                                       |
|------------|--------------------|----------|----------------------------------------------|
| Superadmin | admin@example.com  | admin    | Full access, cannot be blocked/deleted        |
| Admin      | carol@example.com  | carol    | Promoted from User via update_user_role       |
| User       | alice@example.com  | alice    | Booked into 2 events                          |
| User       | bob@example.com    | bob      | Booked into 1 event (fills the meteor shower) |
| User       | dave@example.com   | dave     | Blocked; use to test the blocked-login flow   |

## Bulk logins (for scale/load testing)

`{len(bulk_user_ids)}` synthetic users named `user000001@example.com` through
`user{len(bulk_user_ids):06d}@example.com`, all sharing the password
`Password123`. Every 500th one (`user000500`, `user001000`, ...) is blocked.

## Named events

| Title                 | Starts in | Max bookings | Status                    |
|-----------------------|-----------|--------------|---------------------------|
| Meteor Shower Watch   | 3 days    | 2            | Fully booked (alice, bob) |
| Lunar Eclipse Viewing | 7 days    | 5            | 1 booking (alice)         |
| Planetary Alignment   | 14 days   | 10           | No bookings               |

Plus `{len(bulk_events_with_max)}` synthetic "Stress Test Event NNNN" events spread
across the following year, with randomized capacity (2-50) and bookings.

## To use this database

This replaces the app's default local database, so just start the app
normally - no DATABASE_URL override needed:

```bash
uv run python -m app
```
"""

    with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
        f.write(credentials_doc)

    print(f"\nSample database written to {SAMPLE_DB_PATH}")
    print(f"Credentials written to {CREDENTIALS_PATH}")


if __name__ == "__main__":
    main()
