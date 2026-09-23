from __future__ import annotations

from scripts.size_audit import audit


def test_size_audit_reports_groups_and_duplicate_content(tmp_path):
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "one.dll").write_bytes(b"same")
    (tmp_path / "two.dll").write_bytes(b"same")
    report = audit(tmp_path)
    assert report["total_bytes"] == 8
    assert report["groups_bytes"]["application and other"] == 8
    assert report["duplicate_sets"] == [["runtime/one.dll", "two.dll"]]
