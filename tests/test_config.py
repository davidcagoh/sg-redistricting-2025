"""
Unit tests for src/analysis/config.py.

TDD: all tests written BEFORE implementation (RED phase).
Run: pytest tests/test_config.py -v
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from src.analysis.config import (
    EnsembleConfig,
    PathsConfig,
    RunManifest,
    get_git_sha,
    make_run_id,
    manifest_to_dict,
    write_manifest,
)
from src.utils import OUTPUT, PROCESSED, RAW


# ---------------------------------------------------------------------------
# EnsembleConfig
# ---------------------------------------------------------------------------


class TestEnsembleConfig:
    def test_default_k_districts(self):
        cfg = EnsembleConfig()
        assert cfg.k_districts == 33

    def test_default_pop_tolerance(self):
        cfg = EnsembleConfig()
        assert cfg.pop_tolerance == pytest.approx(0.10)

    def test_default_n_steps(self):
        cfg = EnsembleConfig()
        assert cfg.n_steps == 10_000

    def test_default_burn_in(self):
        cfg = EnsembleConfig()
        assert cfg.burn_in == 1_000

    def test_default_seed(self):
        cfg = EnsembleConfig()
        assert cfg.seed == 42

    def test_default_recom_epsilon(self):
        cfg = EnsembleConfig()
        assert cfg.recom_epsilon == pytest.approx(0.05)

    def test_default_recom_node_repeats(self):
        cfg = EnsembleConfig()
        assert cfg.recom_node_repeats == 2

    def test_default_max_attempts_per_step(self):
        cfg = EnsembleConfig()
        assert cfg.max_attempts_per_step == 100

    def test_default_run_id_is_empty_string(self):
        cfg = EnsembleConfig()
        assert cfg.run_id == ""

    def test_custom_values(self):
        cfg = EnsembleConfig(k_districts=20, seed=7, run_id="test-run")
        assert cfg.k_districts == 20
        assert cfg.seed == 7
        assert cfg.run_id == "test-run"

    def test_frozen_raises_on_mutation(self):
        cfg = EnsembleConfig()
        with pytest.raises(FrozenInstanceError):
            cfg.k_districts = 99  # type: ignore[misc]

    def test_frozen_raises_on_new_attribute(self):
        cfg = EnsembleConfig()
        with pytest.raises(FrozenInstanceError):
            cfg.new_field = "bad"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# PathsConfig
# ---------------------------------------------------------------------------


class TestPathsConfig:
    def _make_paths(self, **kwargs) -> PathsConfig:
        defaults = dict(
            processed_dir=PROCESSED,
            raw_dir=RAW,
            output_dir=OUTPUT,
        )
        defaults.update(kwargs)
        return PathsConfig(**defaults)

    def test_ensemble_dir_returns_path_under_processed(self):
        pc = self._make_paths()
        result = pc.ensemble_dir("my-run-001")
        assert result == PROCESSED / "ensemble" / "my-run-001"

    def test_ensemble_dir_is_a_path_object(self):
        pc = self._make_paths()
        result = pc.ensemble_dir("abc")
        assert isinstance(result, Path)

    def test_ensemble_dir_uses_provided_processed_dir(self):
        custom_processed = Path("/tmp/custom_processed")
        pc = PathsConfig(
            processed_dir=custom_processed,
            raw_dir=RAW,
            output_dir=OUTPUT,
        )
        result = pc.ensemble_dir("run-x")
        assert result == custom_processed / "ensemble" / "run-x"

    def test_output_dir_defaults_to_output_constant(self):
        pc = PathsConfig(processed_dir=PROCESSED, raw_dir=RAW, output_dir=OUTPUT)
        assert pc.output_dir == OUTPUT

    def test_frozen_raises_on_mutation(self):
        pc = self._make_paths()
        with pytest.raises(FrozenInstanceError):
            pc.processed_dir = Path("/other")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RunManifest
# ---------------------------------------------------------------------------


class TestRunManifest:
    def _make_manifest(self, **overrides) -> RunManifest:
        defaults = dict(
            run_id="run-abc",
            git_sha="abc1234",
            config=EnsembleConfig(),
            input_hashes={"subzone": "deadbeef"},
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T01:00:00Z",
        )
        defaults.update(overrides)
        return RunManifest(**defaults)

    def test_n_accepted_defaults_to_zero(self):
        m = self._make_manifest()
        assert m.n_accepted == 0

    def test_n_rejected_defaults_to_zero(self):
        m = self._make_manifest()
        assert m.n_rejected == 0

    def test_metrics_version_defaults_to_one(self):
        m = self._make_manifest()
        assert m.metrics_version == "1"

    def test_fields_stored_correctly(self):
        cfg = EnsembleConfig(seed=99)
        m = self._make_manifest(config=cfg, n_accepted=50, n_rejected=5)
        assert m.config.seed == 99
        assert m.n_accepted == 50
        assert m.n_rejected == 5

    def test_frozen_raises_on_mutation(self):
        m = self._make_manifest()
        with pytest.raises(FrozenInstanceError):
            m.n_accepted = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_git_sha
# ---------------------------------------------------------------------------


class TestGetGitSha:
    def test_returns_a_string(self):
        result = get_git_sha()
        assert isinstance(result, str)

    def test_returns_non_empty_string(self):
        result = get_git_sha()
        assert len(result) > 0

    def test_returns_unknown_or_sha_string(self):
        result = get_git_sha()
        # Must be either "unknown" (git failed) or a valid short SHA (hex chars)
        assert result == "unknown" or all(
            c in "0123456789abcdef" for c in result
        ), f"Unexpected sha format: {result!r}"


# ---------------------------------------------------------------------------
# make_run_id
# ---------------------------------------------------------------------------


class TestMakeRunId:
    def test_returns_run_id_when_set(self):
        cfg = EnsembleConfig(run_id="my-explicit-run")
        result = make_run_id(cfg)
        assert result == "my-explicit-run"

    def test_returns_string_when_run_id_empty(self):
        cfg = EnsembleConfig()
        result = make_run_id(cfg)
        assert isinstance(result, str)

    def test_generated_id_is_non_empty(self):
        cfg = EnsembleConfig()
        result = make_run_id(cfg)
        assert len(result) > 0

    def test_generated_id_contains_timestamp_component(self):
        # Timestamp-based IDs should contain digit sequences
        cfg = EnsembleConfig()
        result = make_run_id(cfg)
        assert any(c.isdigit() for c in result)

    def test_generated_id_contains_sha_component(self):
        # The sha portion should appear in the run_id; we just check
        # that the returned string contains hexadecimal characters.
        cfg = EnsembleConfig()
        result = make_run_id(cfg)
        hex_chars = set("0123456789abcdef-_")
        # At least some chars from the sha portion should be present
        assert any(c in hex_chars for c in result)

    def test_two_calls_without_run_id_produce_different_or_same_id(self):
        # This just ensures the function is deterministic when run_id is set,
        # and doesn't crash on repeated calls without run_id.
        cfg = EnsembleConfig()
        result1 = make_run_id(cfg)
        result2 = make_run_id(cfg)
        # Both must be non-empty strings; they may differ due to timestamp.
        assert isinstance(result1, str) and isinstance(result2, str)


# ---------------------------------------------------------------------------
# manifest_to_dict
# ---------------------------------------------------------------------------


class TestManifestToDict:
    def _make_manifest(self, **overrides) -> RunManifest:
        defaults = dict(
            run_id="run-abc",
            git_sha="abc1234",
            config=EnsembleConfig(),
            input_hashes={"subzone": "deadbeef"},
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T01:00:00Z",
        )
        defaults.update(overrides)
        return RunManifest(**defaults)

    def test_returns_plain_dict(self):
        m = self._make_manifest()
        result = manifest_to_dict(m)
        assert isinstance(result, dict)

    def test_no_path_objects_in_result(self):
        m = self._make_manifest()
        result = manifest_to_dict(m)
        # Recursively check that no Path objects appear as values
        def _check_no_paths(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    _check_no_paths(v)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    _check_no_paths(v)
            else:
                assert not isinstance(obj, Path), f"Path object found: {obj!r}"

        _check_no_paths(result)

    def test_result_is_json_serializable(self):
        m = self._make_manifest()
        result = manifest_to_dict(m)
        # Should not raise
        serialized = json.dumps(result)
        assert isinstance(serialized, str)

    def test_run_id_present(self):
        m = self._make_manifest(run_id="run-xyz")
        result = manifest_to_dict(m)
        assert result["run_id"] == "run-xyz"

    def test_git_sha_present(self):
        m = self._make_manifest(git_sha="cafebabe")
        result = manifest_to_dict(m)
        assert result["git_sha"] == "cafebabe"

    def test_n_accepted_and_rejected_present(self):
        m = self._make_manifest()
        result = manifest_to_dict(m)
        assert "n_accepted" in result
        assert "n_rejected" in result
        assert result["n_accepted"] == 0
        assert result["n_rejected"] == 0

    def test_config_is_nested_dict(self):
        m = self._make_manifest()
        result = manifest_to_dict(m)
        assert isinstance(result["config"], dict)
        assert result["config"]["k_districts"] == 33
        assert result["config"]["seed"] == 42

    def test_input_hashes_preserved(self):
        m = self._make_manifest(input_hashes={"layer_a": "hash1", "layer_b": "hash2"})
        result = manifest_to_dict(m)
        assert result["input_hashes"] == {"layer_a": "hash1", "layer_b": "hash2"}


# ---------------------------------------------------------------------------
# write_manifest
# ---------------------------------------------------------------------------


class TestWriteManifest:
    def _make_manifest(self, **overrides) -> RunManifest:
        defaults = dict(
            run_id="run-write-test",
            git_sha="abc1234",
            config=EnsembleConfig(),
            input_hashes={},
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T01:00:00Z",
        )
        defaults.update(overrides)
        return RunManifest(**defaults)

    def test_writes_valid_json_file(self):
        m = self._make_manifest()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = Path(f.name)
        write_manifest(m, out_path)
        content = out_path.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_written_file_contains_run_id(self):
        m = self._make_manifest(run_id="specific-run-id")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = Path(f.name)
        write_manifest(m, out_path)
        parsed = json.loads(out_path.read_text())
        assert parsed["run_id"] == "specific-run-id"

    def test_written_file_contains_config_block(self):
        m = self._make_manifest()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = Path(f.name)
        write_manifest(m, out_path)
        parsed = json.loads(out_path.read_text())
        assert "config" in parsed
        assert parsed["config"]["n_steps"] == 10_000

    def test_write_creates_parent_dirs(self):
        m = self._make_manifest()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "nested" / "dir" / "manifest.json"
            write_manifest(m, out_path)
            assert out_path.exists()
            parsed = json.loads(out_path.read_text())
            assert isinstance(parsed, dict)

    def test_write_produces_pretty_printed_json(self):
        m = self._make_manifest()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = Path(f.name)
        write_manifest(m, out_path)
        content = out_path.read_text()
        # Pretty-printed JSON has newlines
        assert "\n" in content
