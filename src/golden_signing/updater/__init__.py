"""GitHub Release updater package."""

from golden_signing.updater.apply import (
    ApplyResult,
    UpdateApplyError,
    default_update_dir,
    stage_update,
)
from golden_signing.updater.check import CheckResult, check_for_update
from golden_signing.updater.github import UpdateInfo, UpdateSourceError, fetch_latest_release
from golden_signing.updater.verify import file_sha256, parse_checksums, verify_file_sha256
from golden_signing.updater.version import Version, parse_version

__all__ = [
    "ApplyResult",
    "CheckResult",
    "UpdateApplyError",
    "UpdateInfo",
    "UpdateSourceError",
    "Version",
    "check_for_update",
    "default_update_dir",
    "fetch_latest_release",
    "file_sha256",
    "parse_checksums",
    "parse_version",
    "stage_update",
    "verify_file_sha256",
]
