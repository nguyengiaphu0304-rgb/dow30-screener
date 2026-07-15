"""Integrity-checked, offline-testable snapshot ingestion."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from .quality import DataQualityError

MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024


class IngestionError(RuntimeError):
    """Base error for snapshot acquisition."""


class TransientFetchError(IngestionError):
    """A retryable timeout, connection, rate-limit, or server failure."""


class PermanentFetchError(IngestionError):
    """A non-retryable response or invalid request."""


class Transport(Protocol):
    def fetch(self, url: str, *, timeout_seconds: float) -> bytes: ...


EventSink = Callable[[str, dict[str, object]], None]


@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    source_url: str
    license_note: str
    retrieved_at: datetime
    sha256: str
    byte_size: int
    adjustment_policy: str
    schema_version: int = 1

    def to_json(self) -> str:
        value = asdict(self)
        value["retrieved_at"] = self.retrieved_at.isoformat()
        return json.dumps(value, indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, raw: str) -> SnapshotManifest:
        try:
            value = json.loads(raw)
            if set(value) != {
                "adjustment_policy",
                "byte_size",
                "license_note",
                "retrieved_at",
                "schema_version",
                "sha256",
                "source_url",
            }:
                raise ValueError("unexpected manifest fields")
            manifest = cls(
                source_url=value["source_url"],
                license_note=value["license_note"],
                retrieved_at=datetime.fromisoformat(value["retrieved_at"]),
                sha256=value["sha256"],
                byte_size=value["byte_size"],
                adjustment_policy=value["adjustment_policy"],
                schema_version=value["schema_version"],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise DataQualityError("malformed snapshot manifest") from error
        manifest.validate()
        return manifest

    def validate(self, *, now: datetime | None = None) -> None:
        parsed = urlparse(self.source_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise DataQualityError("manifest source_url must be absolute HTTPS")
        if self.schema_version != 1:
            raise DataQualityError("unsupported manifest schema")
        if not self.license_note.strip() or not self.adjustment_policy.strip():
            raise DataQualityError("license and adjustment policy are required")
        if self.retrieved_at.tzinfo is None:
            raise DataQualityError("retrieved_at must be timezone-aware")
        if self.retrieved_at > (now or datetime.now(UTC)):
            raise DataQualityError("retrieved_at cannot be in the future")
        if self.byte_size <= 0 or self.byte_size > MAX_SNAPSHOT_BYTES:
            raise DataQualityError("invalid snapshot byte size")
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise DataQualityError("invalid SHA-256 digest")


@dataclass(frozen=True, slots=True)
class Snapshot:
    payload: bytes
    manifest: SnapshotManifest
    stale: bool = False


class SnapshotCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.manifest_path = directory / "manifest.json"

    def read(self, *, now: datetime | None = None) -> Snapshot:
        try:
            manifest = SnapshotManifest.from_json(self.manifest_path.read_text(encoding="utf-8"))
            payload = self._payload_path(manifest.sha256).read_bytes()
        except FileNotFoundError as error:
            raise IngestionError("verified cache is missing") from error
        manifest.validate(now=now)
        if len(payload) != manifest.byte_size or sha256(payload).hexdigest() != manifest.sha256:
            raise DataQualityError("cached snapshot integrity check failed")
        return Snapshot(payload, manifest)

    def write(self, snapshot: Snapshot) -> None:
        snapshot.manifest.validate()
        if not snapshot.payload or len(snapshot.payload) > MAX_SNAPSHOT_BYTES:
            raise DataQualityError("snapshot payload size is invalid")
        if len(snapshot.payload) != snapshot.manifest.byte_size:
            raise DataQualityError("snapshot size does not match manifest")
        if sha256(snapshot.payload).hexdigest() != snapshot.manifest.sha256:
            raise DataQualityError("snapshot digest does not match manifest")
        self.directory.mkdir(parents=True, exist_ok=True)
        payload_path = self._payload_path(snapshot.manifest.sha256)
        payload_temp = self._write_temp(snapshot.payload)
        manifest_temp = self._write_temp(snapshot.manifest.to_json().encode())
        try:
            os.replace(payload_temp, payload_path)
            os.replace(manifest_temp, self.manifest_path)
        finally:
            Path(payload_temp).unlink(missing_ok=True)
            Path(manifest_temp).unlink(missing_ok=True)

    def _write_temp(self, value: bytes) -> str:
        descriptor, path = tempfile.mkstemp(dir=self.directory, prefix=".snapshot-")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        return path

    def _payload_path(self, digest: str) -> Path:
        return self.directory / f"snapshot-{digest}.bin"


class SnapshotIngestor:
    def __init__(
        self, transport: Transport, cache: SnapshotCache, event_sink: EventSink | None = None
    ):
        self.transport = transport
        self.cache = cache
        self.emit = event_sink or (lambda _name, _fields: None)

    def acquire(
        self,
        *,
        source_url: str,
        license_note: str,
        adjustment_policy: str,
        now: datetime,
        max_age: timedelta,
        timeout_seconds: float = 10,
        retries: int = 2,
        allow_stale_on_transient_error: bool = False,
    ) -> Snapshot:
        if max_age < timedelta(0):
            raise ValueError("max_age cannot be negative")
        if timeout_seconds <= 0 or retries < 0:
            raise ValueError("timeout must be positive and retries non-negative")
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("source_url must be absolute HTTPS")
        cached: Snapshot | None = None
        try:
            cached = self.cache.read(now=now)
            if cached.manifest.source_url != source_url:
                raise DataQualityError("cache source does not match requested source")
            if now - cached.manifest.retrieved_at <= max_age:
                self.emit(
                    "cache_hit",
                    {"age_seconds": (now - cached.manifest.retrieved_at).total_seconds()},
                )
                return cached
        except IngestionError:
            pass
        for attempt in range(retries + 1):
            try:
                payload = self.transport.fetch(source_url, timeout_seconds=timeout_seconds)
                if not payload or len(payload) > MAX_SNAPSHOT_BYTES:
                    raise DataQualityError("downloaded payload size is invalid")
                manifest = SnapshotManifest(
                    source_url,
                    license_note,
                    now,
                    sha256(payload).hexdigest(),
                    len(payload),
                    adjustment_policy,
                )
                snapshot = Snapshot(payload, manifest)
                self.cache.write(snapshot)
                self.emit("cache_refresh", {"byte_size": len(payload), "attempt": attempt + 1})
                return snapshot
            except TransientFetchError:
                self.emit("retry", {"attempt": attempt + 1})
                if attempt < retries:
                    continue
                if allow_stale_on_transient_error and cached is not None:
                    self.emit(
                        "stale_fallback",
                        {"age_seconds": (now - cached.manifest.retrieved_at).total_seconds()},
                    )
                    return Snapshot(cached.payload, cached.manifest, stale=True)
                raise
        raise AssertionError("unreachable")
