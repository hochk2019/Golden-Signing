from __future__ import annotations

from pathlib import Path

from golden_signing.token.discovery import (
    discover_pkcs11_libraries,
    is_compatible_pkcs11_dll,
    pe_machine,
    pe_machine_label,
    process_is_64bit,
)


def test_process_is_64bit_matches_python() -> None:
    import sys

    assert process_is_64bit() == (sys.maxsize > 2**32)


def test_discovery_excludes_x86_dlls_when_app_is_64bit(tmp_path: Path) -> None:
    x86 = tmp_path / "fake32-pkcs11.dll"
    x64 = tmp_path / "fake64-pkcs11.dll"
    # Minimal MZ + PE headers
    def write_pe(path: Path, machine: int) -> None:
        data = bytearray(0x200)
        data[0:2] = b"MZ"
        data[0x3C:0x40] = (0x80).to_bytes(4, "little")
        data[0x80:0x84] = b"PE\x00\x00"
        data[0x84:0x86] = machine.to_bytes(2, "little")
        path.write_bytes(data)

    write_pe(x86, 0x014C)
    write_pe(x64, 0x8664)
    assert pe_machine(x86) == 0x014C
    assert pe_machine(x64) == 0x8664
    found = discover_pkcs11_libraries(extra_roots=[tmp_path], env={"GOLDEN_SIGNING_PKCS11": ""})
    names = {p.name for p in found}
    if process_is_64bit():
        assert "fake64-pkcs11.dll" in names
        assert "fake32-pkcs11.dll" not in names
        assert not is_compatible_pkcs11_dll(x86)
        assert is_compatible_pkcs11_dll(x64)
    else:
        assert "fake32-pkcs11.dll" in names
    all_libs = discover_pkcs11_libraries(
        extra_roots=[tmp_path],
        env={"GOLDEN_SIGNING_PKCS11": ""},
        include_incompatible=True,
    )
    assert any(p.name == "fake32-pkcs11.dll" for p in all_libs)
    assert pe_machine_label(x64) == "x64"
    assert pe_machine_label(x86) == "x86"
