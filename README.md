<p align="center">
  <img src="src/assets/icon.png" width="300" alt="SpendBook icon">
</p>

<h1 align="center">SpendBook</h1>

<p align="center">
  A simple, offline-first expense and udhaar (credit/debt) tracker built for small shops.
</p>

<p align="center">
  <strong>Status: beta (v0.2.0-beta)</strong> — see <a href="../../releases">Releases</a> for downloadable APKs.
</p>

---

Built with [Flet](https://flet.dev) (Python + Flutter), runs as an
Android app, desktop app, or in the browser, and stores everything
locally in a SQLite database — no account, no internet connection, no
cloud sync required.

Originally built to track day-to-day sales, expenses, and customer credit
for a family shop.

## Features

- **Transactions** — log income and expenses with an amount, label, note,
  and timestamp. Tap any entry to edit it; delete with a confirmation
  step so a mis-tap can't silently erase history. Search by note or
  label.
- **Today's closing summary** — a running total of today's income,
  expense, net, and transaction count, shown above the transaction list.
- **Debts & Dues (udhaar)** — track money customers owe the shop and
  money the shop owes suppliers, separately from day-to-day transactions.
  Entries older than 7 days and still unsettled are flagged "overdue."
  Mark as settled without deleting the history. Search by person or note.
- **Labels** — categorize transactions (e.g. Food, Rent, Sales), each
  with a color picked from a palette. Managed entirely from Settings;
  none are pre-seeded, so the list only ever contains categories you
  actually use.
- **Stats** — a 30-day income/expense/net summary, a spending-by-label
  breakdown, and a 14-day daily trend chart (grouped income/expense bars,
  horizontally scrollable), all computed from the same local database.
- **CSV export** — share a transactions or debts/dues CSV via the
  device's native share sheet.
- **Backup & Restore** — save the full database to your Downloads folder,
  or restore from it. The way to move your data to a new phone: back up
  on the old phone, transfer that one file to the new phone's Downloads
  folder by any means (USB, cloud, etc.), then restore there.
- **First-run setup guide** — a short one-time welcome dialog on a fresh
  install, pointing you at adding your first labels.
- **Works fully offline.** All data lives in a local SQLite file
  (`src/spendbook.db`); nothing is sent anywhere.

## Requirements

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A local Android SDK + Flutter setup is **not required** — see
  "Building the Android APK" below for why.

## Project structure

```
SpendBook/
├── pyproject.toml          # dependencies, app metadata, Android package id
├── .github/
│   └── workflows/
│       └── build-apk.yml    # builds the APK in the cloud on every push
├── src/
│   ├── main.py               # app entry point, navigation, tab/FAB wiring
│   ├── database.py           # all SQLite access -- the only file that
│   │                          #   talks to the database directly
│   ├── theme.py               # color scheme / theme mode
│   ├── assets/
│   │   ├── icon.png            # app icon (universal)
│   │   ├── icon_android.png    # app icon (Android, no transparency)
│   │   └── splash_android.png  # splash screen
│   └── views/
│       ├── transactions.py     # Transactions tab (list, search, closing summary)
│       ├── debts.py            # Debts & Dues tab (list, search, overdue badges)
│       ├── stats.py            # Stats tab (summary, label breakdown, trend chart)
│       ├── add_transaction.py  # add/edit transaction dialog
│       ├── add_debt.py         # add/edit debt dialog
│       ├── settings.py         # labels, export, backup/restore
│       ├── setup_guide.py      # first-run welcome dialog
│       └── ui_helpers.py       # shared error banner + confirm-delete dialog
└── tests/
    ├── conftest.py            # pytest fixture: fresh temp database per test
    └── test_database.py       # tests for database.py (34 tests)
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
> project's pinned version. Some newer controls aren't supported in
> preview and only work in a real APK build. If you hit an
> `Unknown control: ...` error while previewing, that's this limitation
> -- try a real build instead before assuming it's a bug in the app.

## Building the Android APK

### Why this uses GitHub Actions instead of a local build

`flet build apk` needs a full Android SDK + Flutter toolchain on your
machine. In practice, on Windows this repeatedly failed for two separate
reasons that are worth documenting here in case they resurface:

1. **Developer Mode wasn't enabled.** Flutter needs symlink support to
   build with plugins, which Windows only allows once Developer Mode is
   turned on (`Settings → Privacy & security → For developers`).
2. **Flet's own "install Android SDK automatically" prompt didn't
   actually complete the install.** It reported success, but
   `ANDROID_HOME` ended up pointing at an empty/missing folder, and
   `flutter doctor` kept failing the Android toolchain check.

Rather than fight the Windows-specific setup further, the APK is built
in the cloud instead: **`.github/workflows/build-apk.yml`** runs
`flet build apk` on a GitHub-hosted Ubuntu runner, which already has a
working Android SDK preinstalled — no local SDK/Flutter setup needed at
all.

A few extra fixes were needed to make this work in CI specifically:

- `flet build apk` interactively asks "install Flutter SDK now? [y/n]",
  which hangs forever (and then crashes with `EOFError`) in a
  non-interactive CI shell with no terminal to answer it. The workflow
  passes `--yes` to auto-confirm that prompt, and `--no-rich-output` to
  avoid Rich's progress-bar rendering producing garbled CI log output.
- An early attempt to shrink the APK with `--arch arm64` broke the
  build entirely (`[CXX1201] ABIs are not supported for platform`) --
  that flag gets translated internally by `flet-cli` into an Android
  Gradle config, and that translation produced an empty ABI list in
  this Flet version. The workflow uses `--split-per-abi` instead, a
  standard Flutter CLI flag passed straight through with no internal
  translation step, which reliably produces one smaller APK per CPU
  architecture instead of a single "fat" one.

### How to trigger a build

Push to `main` (or click **Run workflow** manually from the Actions tab
if you want to trigger one without pushing new code):

```bash
git add .
git commit -m "your message"
git push
```

Then:

1. Go to your repo on GitHub → the **Actions** tab
2. Open the running/most recent **Build Android APK** workflow
3. Wait for it to finish (green checkmark). It runs the full pytest
   suite first and fails fast if that doesn't pass, before spending time
   on the actual build.
4. Scroll to the bottom of that run's page → **Artifacts** → download
   **spendbook-apk** (a `.zip` containing three APKs, one per CPU
   architecture)
5. Unzip it and install **`app-arm64-v8a-release.apk`** — this covers
   virtually all Android phones from the last several years. Only use
   `app-armeabi-v7a-release.apk` or `app-x86_64-release.apk` if you
   specifically know your device needs one of those.
6. Transfer the `.apk` to your phone (USB, or upload/download via
   Drive/email) and tap it to install. Android will warn about
   installing from an unknown source since it isn't from the Play Store
   — this is expected for a personal build.

This build is debug-signed, which is fine for installing on your own
device. If you ever want to publish to the Play Store, you'll need to
set up a proper release keystore first (a separate, one-time step, not
covered here).

### Android package identifier

Set in `pyproject.toml` under `[tool.flet]` as `org`. This becomes the
app's permanent Android package ID (`org.product`, e.g.
`com.nickcaffienated.spendbook`) — Android treats a build with a
different package ID as a completely different app, and if you ever
publish to the Play Store this ID can't be changed after your first
upload. Don't change it casually once you've started using real builds.

## Releases

Tagged builds are published under [Releases](../../releases) with a
downloadable APK. Current status: **beta** — expect occasional rough
edges, and back up your data (Settings → Backup & Restore) before
updating to a new release. Found a bug? Please
[open an issue](../../issues) with what happened and, if possible, a
screenshot.

## Testing

### Automated tests (database layer)

```bash
uv run pytest         # run all tests
uv run pytest -v      # verbose: show each test name
```

`pytest` is already declared as a dev dependency in `pyproject.toml`, so
`uv sync` installs it automatically. Tests use a fresh temporary SQLite
database per test (see `tests/conftest.py`), so they never touch your
real `spendbook.db`. This same suite runs automatically as the first
step of the GitHub Actions build, so a broken database layer fails fast
instead of wasting a 10+ minute APK build.

### Manual testing checklist (UI)

Automated tests only cover `database.py`. After installing a build, test
the UI by hand:

- Add, edit, and delete a transaction; confirm the balance and today's
  summary update correctly
- Add, edit, settle, and delete a debt/due entry; confirm totals update
- Check the overdue badge appears on unsettled debts older than 7 days
- Search transactions and dues by note/label/person name
- Add and delete labels (with colors) in Settings; confirm the
  transaction dropdown reflects changes immediately
- Export both CSVs from Settings via the share sheet
- Back up, then restore, and confirm all data comes back correctly
- Try invalid input (empty/negative/non-numeric amounts) and confirm you
  get an inline error instead of a crash
- Rotate the phone / resize the window and check nothing overflows the
  screen, and that both list tabs scroll correctly in landscape

## Data & backups

All data lives in a single SQLite file at `src/spendbook.db` (or next to
the installed app's Python files, once built). There is no cloud sync.
Use **Settings → Backup & Restore** to save/restore the full database, or
the CSV export for a spreadsheet-friendly copy. To reset the app
completely, delete `spendbook.db` — it will be recreated empty the next
time the app starts.

## Tech stack

- [Flet](https://flet.dev) — Python UI framework (Flutter under the hood)
- SQLite (via Python's built-in `sqlite3`) — local data storage, no
  external database server
- [pytest](https://pytest.org) — automated tests for the database layer
- [GitHub Actions](https://github.com/features/actions) — cloud APK
  builds, no local Android SDK required
