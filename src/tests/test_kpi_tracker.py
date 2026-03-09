"""Tests for KPI tracker — metrics recording, emergency stop thresholds."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.circuit_breaker import CircuitBreaker
from pipeline.kpi_tracker import KPITracker


@pytest.fixture
def kpi(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))
    cb = CircuitBreaker(state_path=tmp_path / "cb.json")
    return KPITracker(circuit_breaker=cb), cb


class TestKPITracker:
    def test_record_basic_metrics(self, kpi):
        tracker, cb = kpi
        snapshot = tracker.record_metrics(sent=5, opens=3, replies=1)
        assert snapshot.sent_count == 5
        assert snapshot.open_count == 3
        assert snapshot.reply_count == 1
        assert snapshot.emergency_stop is False

    def test_cumulative_metrics(self, kpi):
        tracker, cb = kpi
        tracker.record_metrics(sent=5, opens=3)
        snapshot = tracker.record_metrics(sent=5, opens=2)
        assert snapshot.sent_count == 10
        assert snapshot.open_count == 5

    def test_low_open_rate_triggers_stop(self, kpi):
        tracker, cb = kpi
        # 10 sends, 2 opens = 20% < 30% threshold
        snapshot = tracker.record_metrics(sent=10, opens=2)
        assert snapshot.emergency_stop is True
        assert any("Open rate" in v for v in snapshot.violations)
        # Circuit breakers should be tripped
        assert cb.is_open("instantly")
        assert cb.is_open("ghl")

    def test_high_bounce_rate_triggers_stop(self, kpi):
        tracker, cb = kpi
        # 10 sends, 5 opens, 2 bounces = 20% > 10% threshold
        snapshot = tracker.record_metrics(sent=10, opens=5, bounces=2)
        assert snapshot.emergency_stop is True
        assert any("Bounce rate" in v for v in snapshot.violations)

    def test_zero_replies_after_threshold(self, kpi):
        tracker, cb = kpi
        # 15 sends, 5 opens, 0 replies
        snapshot = tracker.record_metrics(sent=15, opens=5, replies=0)
        assert snapshot.emergency_stop is True
        assert any("0 replies" in v for v in snapshot.violations)

    def test_healthy_metrics_no_stop(self, kpi):
        tracker, cb = kpi
        # Good metrics: 50% open, 10% reply, 0% bounce
        snapshot = tracker.record_metrics(sent=10, opens=5, replies=1, bounces=0)
        assert snapshot.emergency_stop is False
        assert len(snapshot.violations) == 0

    def test_get_latest_kpi(self, kpi):
        tracker, cb = kpi
        tracker.record_metrics(sent=5, opens=3, date_str="2026-03-08")
        snapshot = tracker.get_latest_kpi(date_str="2026-03-08")
        assert snapshot is not None
        assert snapshot.sent_count == 5

    def test_get_latest_kpi_returns_none_without_creating_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
        tracker = KPITracker(circuit_breaker=CircuitBreaker(state_path=tmp_path / "cb.json"))

        snapshot = tracker.get_latest_kpi(date_str="2026-03-09")

        assert snapshot is None
        assert not (tmp_path / "outputs" / "kpi").exists()

    def test_get_latest_kpi_returns_none_for_invalid_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
        kpi_dir = tmp_path / "outputs" / "kpi"
        kpi_dir.mkdir(parents=True, exist_ok=True)
        (kpi_dir / "kpi_2026-03-09.json").write_text("{not-json", encoding="utf-8")
        tracker = KPITracker(circuit_breaker=CircuitBreaker(state_path=tmp_path / "cb.json"))

        snapshot = tracker.get_latest_kpi(date_str="2026-03-09")

        assert snapshot is None

    def test_record_metrics_still_creates_directory_and_latest_loads(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
        tracker = KPITracker(circuit_breaker=CircuitBreaker(state_path=tmp_path / "cb.json"))

        tracker.record_metrics(sent=3, opens=1, date_str="2026-03-09")

        kpi_path = tmp_path / "outputs" / "kpi" / "kpi_2026-03-09.json"
        assert kpi_path.exists()
        saved = json.loads(kpi_path.read_text(encoding="utf-8"))
        assert saved["sent_count"] == 3
        snapshot = tracker.get_latest_kpi(date_str="2026-03-09")
        assert snapshot is not None
        assert snapshot.sent_count == 3
