# Neighbourly

**Cooperative Gig Services Platform for Household and Community Services**  
CSE494 · Lovely Professional University  
Gaurav Kumar · K4E2338  
Course instructor: Dr. Manpreet Singh Sehgal  
Repository: https://github.com/GauravKumar17/CSE494-MongoDb

A working Django website with a MongoDB database, built for a college demonstration. Customers discover providers and book local services; workers manage their profiles and requests; administrators approve profiles and inspect reports. The interface uses a cream, forest-green and peach palette, custom vector illustration, responsive cards and layouts.

## Pages

1. Home with service categories and featured providers
2. Find services with category and locality filters
3. Public worker profile with skills and verified-booking reviews
4. Sign up with customer or worker roles
5. Log in with automatic role-aware routing
6. Customer or worker dashboard
7. Booking request form
8. Booking details, actions and customer review form
9. Worker profile editor
10. Protected administrator dashboard
11. Community and SDG page
12. How it works and FAQ

An account must be signed in to view private booking addresses. Admin is a custom protected Django dashboard, not the ORM-based django.contrib.admin application.

## Quick start

Requirements: Python 3.11 or newer (tested with Python 3.12) and MongoDB Community Server or MongoDB Atlas. Docker is optional.

### 1. Create the Python environment

From the extracted project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell: use `python -m venv .venv` and `.venv\Scripts\Activate.ps1`.

### 2. Configure your environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into `DJANGO_SECRET_KEY` in `.env`. Keep `DJANGO_DEBUG=True` for local development. On Windows, use `Copy-Item .env.example .env`.

The default MongoDB address is `mongodb://localhost:27017/`. If using Atlas, paste your own connection URI into `MONGODB_URI`, configure your network access and give the database user access to the application database. Never commit `.env` or credentials.

### 3. Start MongoDB

Use an existing local MongoDB service, or run the included Docker configuration:

```bash
docker compose up -d
```

The Docker port is bound only to localhost. Do not expose an unauthenticated MongoDB server to the internet. Atlas is also supported through the same environment variable.

### 4. Prepare the database and sample profiles

```bash
python manage.py setup_database
python manage.py seed_demo
```

`setup_database` creates indexes and MongoDB document validators. `seed_demo` is optional, works only in DEBUG mode and adds synthetic profiles labelled **DEMO PROFILE**. It never overwrites existing users or passwords. No SQL database or Django migrations are needed.

### 5. Run the website

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/.

### Development-only demo accounts

Only available after running `seed_demo`:

- Customer: `customer@example.com`
- Worker: `worker@example.com` (Ravi Kumar)
- Administrator: `admin@example.com`
- Password for these seeded accounts: `NeighbourlyDemo!2026`

These credentials are public demonstration credentials, not production accounts. Use a fresh database without demo data for deployment.

To create your own administrator securely:

```bash
python manage.py create_admin --email your-email@example.com --name "Your Name"
```

The command prompts for the password without echoing it. It refuses to overwrite an existing email. Log in at `/login/`, then open `/admin/`.

## Demonstration walkthrough

1. Open the home page and explore service categories.
2. Register as a worker, complete the profile and set a one-hour visit price.
3. Log in as admin and approve that worker.
4. Log in as a customer and find the approved profile by service or locality.
5. Request a visit for a date between tomorrow and 60 days ahead.
6. Log in as the selected worker: accept the request, start the visit and request completion.
7. Log in as the customer: confirm completion and submit one review.
8. Open the admin dashboard to see booking totals and service-demand aggregation.
9. Tick the community-space checkbox on a booking to demonstrate the SDG use case.

A booking reserves exactly one hour. The visit price is stored as a snapshot in integer paise. Materials and additional work are excluded and must be agreed directly. There is no online payment processing and no platform commission.

## MongoDB concepts demonstrated

- Collections: `users`, `worker_profiles`, `bookings`, `reviews`, `sessions`, `rate_limits`.
- Insert: register a customer or create a booking.
- Read: list providers, filter by category/locality and view private booking history.
- Update: edit a profile, approve it or change a booking status.
- Delete: remove server-side session documents on logout (with TTL for expiry).
- Embedded fields: skill arrays and service information in worker profiles.
- References: ObjectId links between accounts, profiles, bookings and reviews.
- Historical snapshots: booking price, worker name and customer name.
- Unique indexes: account email, one profile per worker, one review per booking.
- Partial unique compound index: `(worker_id, slot_key)` where `active` is true. Competing inserts for the same live booking slot cannot both succeed.
- Aggregation: provider review averages and administrator service-demand counts.
- Validators: role/status enums, required BSON fields, nonnegative prices and review bounds.

Categories are a small application-managed list in `market/data.py`, not a separate collection. Category labels are intentionally kept simple for this version.

Booking transitions:

`requested → confirmed → in_progress → completion_pending → completed`

A worker can decline a request. Customers can cancel before work starts. Cancellation and decline deactivate the slot in a single-document update. State updates check the expected prior state to reject stale requests. This implementation does not require multi-document transactions or a replica set.

## Architecture

- `config/`: Django configuration, URL routing and WSGI entry point
- `market/views.py`: page rendering and workflow handlers
- `market/forms.py`: input validation
- `market/db.py`: shared MongoClient and database indexes
- `market/auth.py`: password verification helpers, sessions, role protection and throttling
- `market/middleware.py`: current-user loading and database error handling
- `market/management/commands/`: database setup, administrator creation and demo data
- `templates/`: Django page templates
- `static/`: responsive CSS and small JavaScript enhancements
- `tests/`: functional, access-control and integrity checks

Django is used with direct PyMongo queries. The Django ORM and its SQL-backed authentication/session tables are deliberately not configured. Passwords use Django's password hashing utilities. Sessions use random opaque tokens with only token hashes stored in MongoDB. Session expiry is checked during authentication even if MongoDB's TTL cleanup has not run yet. Logout deletes the session server-side, so replaying the old cookie cannot restore it. CSRF protection covers mutations.

## Testing

```bash
pip install -r requirements-dev.txt
DJANGO_DEBUG=True pytest -q
```

Default tests use a separate in-memory mongomock database, not application data. Tests cover public pages, role access, signup/password hashing, booking conflicts, address privacy, workflow transitions, review eligibility and uniqueness, cancellation/slot release, logout revocation, admin approval, CSRF, malformed inputs and login throttling.

For real MongoDB validation and simultaneous-write tests:

```bash
REAL_MONGO_TEST=1 DJANGO_DEBUG=True pytest -q
```

This uses the configured `MONGODB_URI` and drops/recreates **only** the dedicated `neighbourly_test_automation` database. Never point tests at a production database server. On Windows set these environment variables using PowerShell before running pytest.

Validation performed during creation: Django system check passed; 9 functional tests passed using mongomock. The real-server test was skipped because this execution environment prevented the MongoDB process from starting (`open: Operation not permitted`). Run the real-server suite locally to verify MongoDB validation and concurrent writes. The preview environment does not run this Python virtual environment, so full browser visual QA was unavailable here.

## SDG connection

- **SDG 8**: local visibility, worker choice and transparent service prices.
- **SDG 11**: community maintenance requests for shared spaces.
- **SDG 12**: repair and maintenance instead of unnecessary replacement.

These are product design connections, not proven social impact. Community counts are calculated from completed community bookings. The prototype is not a legally registered cooperative. Profile approval is an administrator review, not certification of qualifications or safety.

## Deployment notes and limitations

This is a college application, not a complete commercial marketplace. There are no real payments, SMS notifications, identity checks, live chat, emergency services or dispute-resolution workflow. Search returns up to 100 recently added approved, available providers. Dashboard history shows the latest 100 bookings while its totals include all matching records. Availability uses fixed one-hour slots; variable-duration jobs need additional scheduling design.

Fonts load from Google Fonts if online; local Arial fallback keeps every page usable offline. No external images or JavaScript frameworks are required.

For a public deployment, use a Python-compatible host, set `DJANGO_DEBUG=False`, configure a unique secret and exact allowed hosts, set `COOKIE_SECURE=True`, put the app behind HTTPS and configure static file serving. Run `python manage.py collectstatic`. A WSGI launch command is `gunicorn config.wsgi:application`. Configure trusted proxy/CSRF origins only for your actual deployment and apply access controls to MongoDB. Tune the simple IP-based authentication throttle for your reverse proxy; it does not trust forwarded headers by default. The app is not compatible with a JavaScript-only static host.

## References

- https://docs.djangoproject.com/en/5.2/
- https://www.mongodb.com/docs/languages/python/pymongo-driver/current/
- https://sdgs.un.org/goals
