"""
Single source of truth for the version shown in Settings. Kept as a
plain constant rather than parsed from pyproject.toml at runtime --
reading arbitrary files from inside a packaged Android APK is untested
in this app and not worth the risk for something this simple. Update
this alongside pyproject.toml's [project] version when cutting a release.
"""

APP_VERSION = "0.5.2-beta"
RELEASES_URL = "https://github.com/caffienated-nick/SpendBook/releases"