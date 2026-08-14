<p align="center">
  <img src="src/assets/icon.png" width="320" alt="SpendBook icon">
</p>

<h1 align="center">SpendBook</h1>

<p align="center">
  A simple, offline-first expense and udhaar (credit/debt) tracker built for small shops.
</p>

<p align="center">
  <strong>Status: v1.0.1</strong> — see <a href="../../releases">Releases</a> for downloadable APKs.
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
  Unsettled entries older than a configurable threshold (default 7 days)
  are flagged "overdue." Mark as settled without deleting the history.
  Search by person or note.
- **Labels** — categorize transactions (e.g. Food, Rent, Sales), each
  with a color picked from a palette. Managed entirely from Settings;
  none are pre-seeded, so the list only ever contains categories you
  actually use.
- **Stats** — income/expense/net summary over a selectable window
  (7/30/90 days), a period-over-period comparison ("up/down vs previous
  window"), transaction count and averages, largest single income/
  expense, a spending-by-label breakdown, and a 14-day daily trend chart
  (grouped income/expense bars, horizontally scrollable).
- **CSV export** — share a transactions or debts/dues CSV via the
  device's native share sheet.
- **Backup & Restore** — save the full database on-device, or restore
  from it. A "Share backup file" button sends the backup directly via
  Android's native share sheet — the practical way to move your data to
  a new phone, and a workaround for a known Android/Flutter quirk where
  the backup's folder isn't visible in every file manager (the backup
  itself still saves and restores correctly either way).
- **Automatic backups during use** — beyond the manual button, the app
  quietly backs itself up about 30 seconds after you stop making changes
  (adding, editing, deleting, or settling anything), so you don't have
  to remember to do it yourself. A burst of activity collapses into one
  backup, not one per action, so this stays lightweight. Backups also
  run automatically right after an update is detected.
- **First-run setup guide** — a short one-time welcome dialog on a fresh
  install, pointing you at adding your first labels.
- **Manual update check** — Settings shows the current version and a
  button that opens this repo's Releases page in your browser. No
  auto-download or auto-install; you choose when to update.
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
│       └── build-apk.yml    # builds + signs the APK in the cloud on every push
├── src/
│   ├── main.py               # app entry point, navigation, tab/FAB wiring,
│   │                          #   wraps view refresh() calls to trigger auto-backup
│   ├── database.py           # all SQLite access + schema migrations --
│   │                          #   the only file that talks to the database
│   ├── theme.py               # color scheme / theme mode
│   ├── version.py             # app version + Releases URL (Settings display)
│   ├── assets/
│   │   ├── icon.png            # app icon (universal)
│   │   ├── icon_android.png    # app icon (Android, no transparency)
│   │   └── splash_android.png  # splash screen
│   └── views/
│       ├── transactions.py     # Transactions tab (list, search, closing summary)
│       ├── debts.py            # Debts & Dues tab (list, search, overdue badges)
│       ├── stats.py            # Stats tab (summary, comparison, breakdown, chart)
│       ├── add_transaction.py  # add/edit transaction dialog
│       ├── add_debt.py         # add/edit debt dialog
│       ├── settings.py         # labels, export, backup/restore, preferences, about
│       ├── setup_guide.py      # first-run welcome dialog
│       ├── auto_backup.py      # debounced auto-backup timer, triggered after
│       │                       #   any data change anywhere in the app
│       └── ui_helpers.py       # shared error banner + confirm-delete dialog
└── tests/
    ├── conftest.py            # pytest fixture: fresh temp database per test
    └── test_database.py       # tests for database.py (53 tests)
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
uv run flet run --android
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

### Signing (so updates install in place)

By default, `flet build apk` signs with a fresh debug key on every
build, which means Android treats each downloaded APK as a different
app and refuses to update in place — forcing an uninstall every time.

The workflow supports signing with a **stable release keystore** instead,
via two optional repo secrets:

- `ANDROID_KEYSTORE_BASE64` — a keystore file (`keytool -genkey ...`),
  base64-encoded (`base64 -w0 my-key.jks`)
- `ANDROID_KEYSTORE_PASSWORD` — its password

If these aren't set, the build falls back to debug signing automatically
(the workflow checks for this in plain bash, not a GitHub Actions `if:`
condition — the `secrets` context isn't allowed there, a real platform
restriction that's easy to hit by accident).

**Keep the `.jks` file and its password somewhere safe outside the
repo.** If either is lost, a new keystore has to be generated, and
every existing install will need to be uninstalled once more to move
to the new key.

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

### Android package identifier

Set in `pyproject.toml` under `[tool.flet]` as `org`. This becomes the
app's permanent Android package ID (`org.product`, e.g.
`com.nickcaffienated.spendbook`) — Android treats a build with a
different package ID as a completely different app, and if you ever
publish to the Play Store this ID can't be changed after your first
upload. Don't change it casually once you've started using real builds.

## Releases

Tagged builds are published under [Releases](../../releases) with a
downloadable APK. As of v1.0.0, SpendBook has moved past beta: the core
features have been used and tested in real day-to-day shop use, and the
issues found along the way (see release history) have been fixed. It's
still a small, actively-maintained project though, not a polished
commercial app — back up your data (Settings → Backup & Restore, or
rely on the automatic backups) before updating to a new release, same
as you would for any app you depend on daily. Found a bug? Please
[open an issue](../../issues) with what happened and, if possible, a
screenshot.

The app itself has a manual update check (Settings → About → "Check for
updates"), which just opens this Releases page in your browser — there's
no auto-download or auto-install.

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

Coverage includes the schema migration system itself: a simulated
pre-migration database with real data (confirming it upgrades without
data loss), repeated-startup safety, and a deliberately broken migration
(confirming it rolls back cleanly instead of corrupting the schema); and
version-change detection used to trigger auto-backup after an update.

### Manual testing checklist (UI)

Automated tests only cover `database.py`. After installing a build, test
the UI by hand:

- Add, edit, and delete a transaction; confirm the balance and today's
  summary update correctly
- Add, edit, settle, and delete a debt/due entry; confirm totals update
- Change the overdue threshold in Settings → Preferences and confirm the
  badge behavior actually changes
- Change the Stats window (7/30/90 days) and confirm the summary,
  comparison, and label breakdown all update
- Search transactions and dues by note/label/person name
- Add and delete labels (with colors) in Settings; confirm the
  transaction dropdown reflects changes immediately
- Export both CSVs from Settings via the share sheet
- Back up, then restore, and confirm all data (including labels) comes
  back correctly without needing to restart the app
- Tap "Share backup file" and confirm the share sheet opens with a real
  backup file attached
- Make a change, wait ~30 seconds without touching anything else, and
  confirm a fresh auto-backup was created (share it to check its
  timestamp, since the folder itself may not be visible on your device)
- Tap "Check for updates" in Settings and confirm the dialog opens, and
  that "Open in browser" actually opens the Releases page
- Install a new release **without** uninstalling the previous one first,
  and confirm it updates in place rather than requiring a fresh install
- Try invalid input (empty/negative/non-numeric amounts) and confirm you
  get an inline error instead of a crash
- Check nothing overflows the screen in normal (portrait) use. Landscape
  is not actively verified -- see Known limitations.

## Data & backups

All data lives in a single SQLite file at `src/spendbook.db` (or next to
the installed app's Python files, once built). There is no cloud sync.
The app backs itself up automatically (see Features above), and
**Settings → Backup & Restore** can also trigger one manually or restore
from it. On some devices the backup's folder isn't visible in a file
manager (a known Android/Flutter platform quirk); use the **Share
backup file** button there to get the file out via the share sheet
instead. The CSV export is available for a spreadsheet-friendly copy.
To reset the app completely, delete `spendbook.db` — it will be
recreated empty the next time the app starts.

Schema changes across versions are handled by a migration system in
`database.py` (see the `MIGRATIONS` list and the template comment above
it) — upgrading to a newer version should never require deleting your
data, even when the database structure itself changes.

## Known limitations

- No cloud sync — this is intentional; backups are automatic but still
  local-only
- Landscape orientation isn't fully reliable on some devices (observed
  on at least one non-Pixel Android phone, where scrolling doesn't work
  correctly in landscape). The app is designed and tested for portrait
  use; landscape works on most devices but isn't actively maintained,
  since portrait is the intended way to use it.
- Testing has been done on a small number of real devices (primarily
  Pixel and one Samsung phone). If something looks or behaves
  differently on your device, please report it.

## Contributors

- [@caffienated-nick](https://github.com/caffienated-nick) — Creator & Developer
- [@zazriel](https://github.com/zazriel) — Beta Tester

## Tech stack

- [Flet](https://flet.dev) — Python UI framework (Flutter under the hood)
- SQLite (via Python's built-in `sqlite3`) — local data storage, no
  external database server
- [pytest](https://pytest.org) — automated tests for the database layer
- [GitHub Actions](https://github.com/features/actions) — cloud APK
  builds, no local Android SDK required