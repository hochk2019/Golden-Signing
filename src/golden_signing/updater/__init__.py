"""GitHub Release updater package."""

from golden_signing.updater.apply import (
    ApplyResult,
    InstallerResult,
    UpdateApplyError,
    default_update_dir,
    stage_installer,
    stage_update,
)
from golden_signing.updater.check import (
    DEFAULT_UPDATE_REPO,
    CheckResult,
    check_for_update,
    resolve_repo,
)
from golden_signing.updater.github import UpdateInfo, UpdateSourceError, fetch_latest_release
from golden_signing.updater.runtime import app_install_dir, is_frozen, relaunch_app
from golden_signing.updater.verify import file_sha256, parse_checksums, verify_file_sha256
from golden_signing.updater.version import Version, parse_version

__all__ = [
    "ApplyResult",
    "CheckResult",
    "DEFAULT_UPDATE_REPO",
    "InstallerResult",
    "UpdateApplyError",
    "UpdateInfo",
    "UpdateSourceError",
    "Version",
    "app_install_dir",
    "check_for_update",
    "default_update_dir",
    "fetch_latest_release",
    "file_sha256",
    "is_frozen",
    "parse_checksums",
    "parse_version",
    "relaunch_app",
    "resolve_repo",
    "stage_installer",
    "stage_update",
    "verify_file_sha256",
]
