"""Unit tests for PKCS#11 discovery (T2)."""

from __future__ import annotations

from pathlib import Path

from golden_signing.token.discovery import ENV_PKCS11, discover_pkcs11_libraries


def test_env_override_wins(tmp_path: Path) -> None:
    dll = tmp_path / "vendor-pkcs11.dll"
    dll.write_bytes(b"MZ-fake")
    env = {ENV_PKCS11: str(dll)}
    found = discover_pkcs11_libraries(env=env, extra_roots=None)
    assert found
    assert found[0] == dll.resolve()


def test_env_multiple_paths(tmp_path: Path) -> None:
    a = tmp_path / "a-pkcs11.dll"
    b = tmp_path / "b-pkcs11.dll"
    a.write_bytes(b"MZ")
    b.write_bytes(b"MZ")
    env = {ENV_PKCS11: f"{a};{b}"}
    found = discover_pkcs11_libraries(env=env)
    assert len(found) >= 2
    assert a.resolve() in found
    assert b.resolve() in found


def test_missing_env_path_filtered(tmp_path: Path) -> None:
    env = {ENV_PKCS11: str(tmp_path / "nope-pkcs11.dll")}
    found = discover_pkcs11_libraries(env=env, extra_roots=[tmp_path])
    assert all(p.is_file() for p in found)
    assert tmp_path / "nope-pkcs11.dll" not in found


def test_extra_roots_scan(tmp_path: Path) -> None:
    dll = tmp_path / "my-pkcs11-module.dll"
    dll.write_bytes(b"MZ")
    other = tmp_path / "readme.txt"
    other.write_text("x")
    found = discover_pkcs11_libraries(env={}, extra_roots=[tmp_path])
    assert dll.resolve() in found
    assert other.resolve() not in found


def test_discovery_does_not_load_dll(tmp_path: Path) -> None:
    # A non-DLL file with pkcs11 in the name is still only existence-checked.
    fake = tmp_path / "not-really-pkcs11.dll"
    fake.write_text("this is not a PE")
    found = discover_pkcs11_libraries(env={ENV_PKCS11: str(fake)})
    assert found == [fake.resolve()]
