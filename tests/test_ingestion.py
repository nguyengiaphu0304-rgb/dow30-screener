from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dow30_screener import (
    DataQualityError,
    PermanentFetchError,
    Snapshot,
    SnapshotCache,
    SnapshotIngestor,
    SnapshotManifest,
    TransientFetchError,
)
from dow30_screener import ingestion as ingestion_module

NOW = datetime(2026, 1, 10, tzinfo=UTC)
URL = "https://example.com/prices.csv"


class FakeTransport:
    def __init__(self, outcomes: list[bytes | Exception]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def fetch(self, url: str, *, timeout_seconds: float) -> bytes:
        assert url == URL and timeout_seconds > 0
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def ingestor(tmp_path: Path, outcomes: list[bytes | Exception], events=None):
    transport = FakeTransport(outcomes)
    return SnapshotIngestor(transport, SnapshotCache(tmp_path), events), transport


def acquire(service: SnapshotIngestor, **overrides):
    values = dict(
        source_url=URL,
        license_note="CC0 synthetic fixture",
        adjustment_policy="unadjusted synthetic",
        now=NOW,
        max_age=timedelta(days=1),
    )
    values.update(overrides)
    return service.acquire(**values)


def test_refresh_writes_and_verifies_manifest(tmp_path: Path) -> None:
    service, transport = ingestor(tmp_path, [b"date,ticker\n2026-01-01,AAA\n"])
    result = acquire(service)
    assert result.payload.startswith(b"date") and not result.stale
    assert result.manifest.byte_size == len(result.payload)
    assert SnapshotCache(tmp_path).read(now=NOW) == result
    assert transport.calls == 1


def test_fresh_cache_avoids_network_at_exact_boundary(tmp_path: Path) -> None:
    first, _ = ingestor(tmp_path, [b"fixture"])
    acquire(first)
    second, transport = ingestor(tmp_path, [])
    result = acquire(second, now=NOW + timedelta(days=1))
    assert result.payload == b"fixture" and transport.calls == 0


@pytest.mark.parametrize("part", ["payload", "manifest"])
def test_corrupt_cache_fails_closed(tmp_path: Path, part: str) -> None:
    service, _ = ingestor(tmp_path, [b"fixture"])
    acquire(service)
    manifest = SnapshotCache(tmp_path).read(now=NOW).manifest
    path = (
        tmp_path / f"snapshot-{manifest.sha256}.bin"
        if part == "payload"
        else tmp_path / "manifest.json"
    )
    path.write_bytes(b"corrupt")
    with pytest.raises(DataQualityError):
        acquire(service, now=NOW + timedelta(days=2))


def test_transient_failure_retries_then_refreshes(tmp_path: Path) -> None:
    events = []
    service, transport = ingestor(
        tmp_path,
        [TransientFetchError("timeout"), b"ok"],
        lambda name, fields: events.append((name, fields)),
    )
    result = acquire(service)
    assert result.payload == b"ok" and transport.calls == 2
    assert [name for name, _ in events] == ["retry", "cache_refresh"]


def test_stale_fallback_requires_explicit_policy(tmp_path: Path) -> None:
    service, _ = ingestor(tmp_path, [b"old"])
    acquire(service)
    stale, _ = ingestor(tmp_path, [TransientFetchError("offline")])
    with pytest.raises(TransientFetchError):
        acquire(stale, now=NOW + timedelta(days=2), retries=0)
    stale, _ = ingestor(tmp_path, [TransientFetchError("offline")])
    result = acquire(
        stale, now=NOW + timedelta(days=2), retries=0, allow_stale_on_transient_error=True
    )
    assert result.stale and result.payload == b"old"


def test_permanent_error_never_uses_stale_cache(tmp_path: Path) -> None:
    service, _ = ingestor(tmp_path, [b"old"])
    acquire(service)
    failed, transport = ingestor(tmp_path, [PermanentFetchError("404")])
    with pytest.raises(PermanentFetchError):
        acquire(failed, now=NOW + timedelta(days=2), allow_stale_on_transient_error=True)
    assert transport.calls == 1


@pytest.mark.parametrize("payload", [b"", b"x" * (10 * 1024 * 1024 + 1)])
def test_rejects_invalid_download_size(tmp_path: Path, payload: bytes) -> None:
    service, _ = ingestor(tmp_path, [payload])
    with pytest.raises(DataQualityError, match="size"):
        acquire(service)


def test_manifest_rejects_unknown_schema_and_future_time() -> None:
    valid = SnapshotManifest(URL, "CC0", NOW, "0" * 64, 1, "unadjusted")
    with pytest.raises(DataQualityError, match="schema"):
        replace(valid, schema_version=2).validate()
    with pytest.raises(DataQualityError, match="future"):
        valid.validate(now=NOW - timedelta(seconds=1))


def test_cache_write_rejects_digest_mismatch(tmp_path: Path) -> None:
    manifest = SnapshotManifest(URL, "CC0", NOW, "0" * 64, 3, "unadjusted")
    with pytest.raises(DataQualityError, match="digest"):
        SnapshotCache(tmp_path).write(Snapshot(b"abc", manifest))


def test_failed_manifest_swap_preserves_previous_verified_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _ = ingestor(tmp_path, [b"old"])
    acquire(first)
    real_replace = ingestion_module.os.replace
    calls = 0

    def fail_manifest_swap(source: str, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated interrupted refresh")
        real_replace(source, destination)

    monkeypatch.setattr(ingestion_module.os, "replace", fail_manifest_swap)
    refresh, _ = ingestor(tmp_path, [b"new"])
    with pytest.raises(OSError, match="interrupted"):
        acquire(refresh, now=NOW + timedelta(days=2))
    assert SnapshotCache(tmp_path).read(now=NOW + timedelta(days=2)).payload == b"old"


@pytest.mark.parametrize("max_age", [timedelta(seconds=-1)])
def test_rejects_negative_age(tmp_path: Path, max_age: timedelta) -> None:
    service, _ = ingestor(tmp_path, [b"unused"])
    with pytest.raises(ValueError, match="max_age"):
        acquire(service, max_age=max_age)
