# SpendBook

A simple, offline-first expense and udhaar (credit/debt) tracker built for
small shops. Built with [Flet](https://flet.dev) (Python + Flutter), runs
as an Android app, desktop app, or in the browser, and stores everything
locally in a SQLite database — no account, no internet connection, no
cloud sync required.

Originally built to track day-to-day sales, expenses, and customer credit
for a family shop.

## Features

- **Transactions** — log income and expenses with an amount, label, note,
  and timestamp. Tap any entry to edit it; delete with a confirmation
  step so a mis-tap can't silently erase history.
- **Today's closing summary** — a running total of today's income,
  expense, net, and transaction count, shown above the transaction list.
- **Debts & Dues (udhaar)** — track money customers owe the shop and
  money the shop owes suppliers, separately from day-to-day transactions.
  Entries older than 7 days and still unsettled are flagged "overdue."
  Mark as settled without deleting the history.
- **Labels** — categorize transactions (e.g. Food, Rent, Sales). Managed
  entirely from Settings; none are pre-seeded, so the list only ever
  contains categories you actually use.
- **Stats** — a 30-day income/expense/net summary, a spending-by-label
  breakdown, and a 14-day daily trend, all computed from the same local
  database.
- **CSV export** — export transactions or debts/dues to a CSV file
  through the device's native save dialog. (Requires a real APK build —
  see note under Testing below.)
- **Optional PIN lock** — off by default. When enabled in Settings, the
  app opens to a PIN entry screen before showing any data.
- **Works fully offline.** All data lives in a local SQLite file
  (`src/spendbook.db`); nothing is sent anywhere.

## Requirements

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- For building an actual Android APK: Android SDK + Flutter, which
  `flet build apk` will download automatically on first run if missing
  (requires an internet connection and can take a while the first time)

## Project structure

```
SpendBook/
├── pyproject.toml          # dependencies, app metadata, Android package id
├── src/
│   ├── main.py              # app entry point, navigation, PIN-lock gate
│   ├── database.py          # all SQLite access -- the only file that
│   │                         #   talks to the database directly
│   ├── theme.py              # color scheme / theme mode
│   ├── assets/
│   │   ├── icon.png           # app icon (universal)
│   │   ├── icon_android.png   # app icon (Android, no transparency)
│   │   └── splash_android.png # splash screen
│   └── views/
│       ├── transactions.py    # Transactions tab
│       ├── debts.py           # Debts & Dues tab
│       ├── stats.py           # Stats tab
│       ├── add_transaction.py # add/edit transaction dialog
│       ├── add_debt.py        # add/edit debt dialog
│       ├── settings.py        # labels, export, PIN lock toggle
│       ├── pin_lock.py        # PIN entry screen
│       └── ui_helpers.py      # shared error banner + confirm-delete dialog
└── tests/
    ├── conftest.py           # pytest fixture: fresh temp database per test
    └── test_database.py      # tests for database.py
```

## Running the app (development)

Install dependencies:

```bash
uv sync
```

Run as a desktop app:

```bash
uv run flet run
```

Run as a web app (in your browser):

```bash
uv run flet run --web
```

Preview on your Android phone without building an APK — install the
**Flet** app from the Play Store, then run:

```bash
uv run flet run
```

and scan the QR code it prints with the Flet app (phone and PC must be on
the same Wi-Fi network).

> **Known limitation of this preview mode:** the Flet mobile preview app
> bundles its own fixed Flet client version, independent of this
> project's pinned version. Some newer controls (e.g. the file picker
> used for CSV export) may not work in preview and will only work in a
> real APK build — see below.

## Building the Android APK

```bash
uv run flet build apk
```

On the first run this will download the JDK, Android SDK, and Flutter if
they aren't already installed — this needs an internet connection and can
take 10–20+ minutes the first time; rebuilds after that are much faster.

The resulting `.apk` will be in `build/apk/`. Copy it to your phone and
open it to install (Android will warn about installing from an unknown
source since it isn't from the Play Store — this is expected).

This build is debug-signed, which is fine for installing on your own
device. If you ever want to publish to the Play Store, you'll need to set
up a proper release keystore first (a separate, one-time step, not
covered here).

### Android package identifier

Set in `pyproject.toml` under `[tool.flet]` as `org`. This becomes the
app's permanent Android package ID (`org.product`, e.g.
`com.nickcaffienated.spendbook`) — Android treats a build with a
different package ID as a completely different app, and if you ever
publish to the Play Store this ID can't be changed after your first
upload. Don't change it casually once you've started using real builds.

## Testing

### Automated tests (database layer)

```bash
uv add --dev pytest   # first time only
uv run pytest         # run all tests
uv run pytest -v      # verbose: show each test name
```

Tests use a fresh temporary SQLite database per test (see
`tests/conftest.py`), so they never touch your real `spendbook.db`.

### Manual testing checklist (UI)

Automated tests only cover `database.py`. After building, test the UI
by hand:

- Add, edit, and delete a transaction; confirm the balance and today's
  summary update correctly
- Add, edit, settle, and delete a debt/due entry; confirm totals update
- Check the overdue badge appears on unsettled debts older than 7 days
- Add and delete labels in Settings; confirm the transaction dropdown
  reflects changes immediately
- **Export both CSVs from Settings and open the resulting files** — this
  specifically needs a real APK build, not the `flet run` preview
- Toggle the PIN lock on, close and reopen the app, confirm it locks;
  toggle it off, confirm it doesn't
- Try invalid input (empty/negative/non-numeric amounts) and confirm you
  get an inline error instead of a crash
- Rotate the phone / resize the window and check nothing overflows the
  screen

## Data & backups

All data lives in a single SQLite file at `src/spendbook.db` (or next to
the installed app's Python files, once built). There is no cloud sync.
To back up your data, copy that file somewhere safe, or use the CSV
export in Settings. To reset the app completely, delete that file — it
will be recreated empty the next time the app starts.

## Tech stack

- [Flet](https://flet.dev) — Python UI framework (Flutter under the hood)
- SQLite (via Python's built-in `sqlite3`) — local data storage, no
  external database server
- [pytest](https://pytest.org) — automated tests for the database layer