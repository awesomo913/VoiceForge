"""Tests for build.py's rubberband-vendoring helpers (checksum verification +
file discovery). Does NOT invoke PyInstaller or produce a real build — that's
exercised manually (see CHANGELOG/commit messages), not in the fast test
suite. Importing build.py itself has no side effects (no module-level code
runs PyInstaller; that only happens inside build_exe()/main()).
"""
import hashlib

import pytest

import build


@pytest.fixture(autouse=True)
def _reset_vendor_dir(monkeypatch):
    """Every test points build.VENDOR_RUBBERBAND_DIR at its own tmp_path via
    the test function's own fixture use — this just guarantees the module
    constant is restored afterward regardless."""
    original = build.VENDOR_RUBBERBAND_DIR
    original_hash = build.VENDOR_RUBBERBAND_SHA256
    yield
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_DIR", original, raising=False)
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_SHA256", original_hash, raising=False)


def test_missing_vendor_dir_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_DIR", str(tmp_path / "does_not_exist"))
    assert build._find_vendored_rubberband_binaries() == []


def test_vendor_dir_without_exe_returns_empty(monkeypatch, tmp_path):
    vendor_dir = tmp_path / "vendor" / "rubberband"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "readme.txt").write_text("not the exe")
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_DIR", str(vendor_dir))
    assert build._find_vendored_rubberband_binaries() == []


def test_vendor_dir_with_exe_only_returns_it(monkeypatch, tmp_path):
    vendor_dir = tmp_path / "vendor" / "rubberband"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "rubberband.exe").write_bytes(b"fake exe bytes")
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_DIR", str(vendor_dir))
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_SHA256", None)

    result = build._find_vendored_rubberband_binaries()

    assert len(result) == 1
    path, dest = result[0]
    assert path.endswith("rubberband.exe")
    assert dest == "vendor/rubberband"


def test_nested_support_files_are_not_silently_dropped(monkeypatch, tmp_path):
    """Regression test: a real CLI tool distribution sometimes ships support
    files in a subfolder (e.g. lib/ or licenses/) — these used to be silently
    skipped (only os.listdir() of the top level was checked), so the build
    would succeed while quietly shipping an incomplete rubberband install."""
    vendor_dir = tmp_path / "vendor" / "rubberband"
    (vendor_dir / "lib").mkdir(parents=True)
    (vendor_dir / "rubberband.exe").write_bytes(b"fake exe bytes")
    (vendor_dir / "lib" / "support.dll").write_bytes(b"fake dll bytes")
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_DIR", str(vendor_dir))
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_SHA256", None)

    result = build._find_vendored_rubberband_binaries()

    dest_by_name = {path.replace("\\", "/").rsplit("/", 1)[-1]: dest for path, dest in result}
    assert dest_by_name["rubberband.exe"] == "vendor/rubberband"
    assert dest_by_name["support.dll"] == "vendor/rubberband/lib"


def test_checksum_mismatch_aborts_the_build(monkeypatch, tmp_path):
    vendor_dir = tmp_path / "vendor" / "rubberband"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "rubberband.exe").write_bytes(b"fake exe bytes")
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_DIR", str(vendor_dir))
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_SHA256", "0" * 64)

    with pytest.raises(SystemExit):
        build._find_vendored_rubberband_binaries()


def test_checksum_match_succeeds(monkeypatch, tmp_path):
    vendor_dir = tmp_path / "vendor" / "rubberband"
    vendor_dir.mkdir(parents=True)
    content = b"fake exe bytes"
    (vendor_dir / "rubberband.exe").write_bytes(content)
    real_hash = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_DIR", str(vendor_dir))
    monkeypatch.setattr(build, "VENDOR_RUBBERBAND_SHA256", real_hash)

    result = build._find_vendored_rubberband_binaries()

    assert len(result) == 1


def test_sha256_matches_hashlib():
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"some content")
        path = f.name
    try:
        assert build._sha256(path) == hashlib.sha256(b"some content").hexdigest()
    finally:
        import os
        os.unlink(path)
