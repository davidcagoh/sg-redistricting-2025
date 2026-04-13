"""
Tests for src/analysis/mcmc/acceptance.py — RED phase.

make_acceptance(config) must return gerrychain.accept.always_accept.
make_tempered_acceptance(beta) must raise NotImplementedError.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.analysis.config import EnsembleConfig
from src.analysis.mcmc.acceptance import make_acceptance, make_tempered_acceptance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs) -> EnsembleConfig:
    defaults = dict(
        k_districts=5,
        pop_tolerance=0.10,
        n_steps=100,
        burn_in=10,
        seed=0,
        recom_epsilon=0.05,
        recom_node_repeats=1,
        max_attempts_per_step=10,
        run_id="test-run",
    )
    defaults.update(kwargs)
    return EnsembleConfig(**defaults)


# ---------------------------------------------------------------------------
# make_acceptance — return type
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_make_acceptance_returns_callable():
    config = _make_config()
    result = make_acceptance(config)
    assert callable(result), "make_acceptance must return a callable"


@pytest.mark.unit
def test_make_acceptance_returns_always_accept():
    """make_acceptance must return gerrychain.accept.always_accept itself."""
    from gerrychain.accept import always_accept

    config = _make_config()
    result = make_acceptance(config)
    assert result is always_accept, (
        "make_acceptance must return gerrychain.accept.always_accept"
    )


@pytest.mark.unit
def test_make_acceptance_config_independent():
    """
    Any config must yield the same callable (always_accept is uniform ensemble;
    config parameters do not influence which acceptance function is used).
    """
    configs = [
        _make_config(pop_tolerance=0.05),
        _make_config(pop_tolerance=0.20),
        _make_config(k_districts=10),
        _make_config(seed=999),
    ]
    results = [make_acceptance(c) for c in configs]
    first = results[0]
    for i, r in enumerate(results[1:], start=1):
        assert r is first, (
            f"make_acceptance must return the same callable for all configs; "
            f"config index {i} returned a different object"
        )


# ---------------------------------------------------------------------------
# make_acceptance — duck-type: returned function accepts a partition argument
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_make_acceptance_returned_fn_accepts_partition():
    """
    The returned callable must accept a single partition argument and
    return True (always_accept always returns True).
    """
    config = _make_config()
    accept_fn = make_acceptance(config)

    mock_partition = MagicMock()
    result = accept_fn(mock_partition)

    assert result is True, (
        "always_accept must return True for any partition"
    )


@pytest.mark.unit
def test_make_acceptance_returned_fn_always_true_multiple_calls():
    """
    always_accept must return True on every call, not just the first.
    """
    config = _make_config()
    accept_fn = make_acceptance(config)

    for i in range(10):
        mock_partition = MagicMock()
        assert accept_fn(mock_partition) is True, (
            f"always_accept returned non-True on call {i}"
        )


# ---------------------------------------------------------------------------
# make_tempered_acceptance — must raise NotImplementedError
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_make_tempered_acceptance_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        make_tempered_acceptance(1.0)


@pytest.mark.unit
def test_make_tempered_acceptance_raises_for_zero_beta():
    with pytest.raises(NotImplementedError):
        make_tempered_acceptance(0.0)


@pytest.mark.unit
def test_make_tempered_acceptance_raises_for_negative_beta():
    with pytest.raises(NotImplementedError):
        make_tempered_acceptance(-0.5)


@pytest.mark.unit
def test_make_tempered_acceptance_raises_for_large_beta():
    with pytest.raises(NotImplementedError):
        make_tempered_acceptance(1_000_000.0)


@pytest.mark.unit
def test_make_tempered_acceptance_error_message_mentions_not_needed():
    """
    The NotImplementedError message should communicate that tempered acceptance
    is not needed for a uniform ensemble (helps future maintainers).
    """
    with pytest.raises(NotImplementedError, match=r"(?i)uniform"):
        make_tempered_acceptance(0.5)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_make_acceptance_with_minimal_config():
    """Minimal config with all fields at boundary values."""
    config = EnsembleConfig(
        k_districts=1,
        pop_tolerance=0.0,
        n_steps=1,
        burn_in=0,
        seed=0,
        recom_epsilon=0.0,
        recom_node_repeats=1,
        max_attempts_per_step=1,
        run_id="",
    )
    result = make_acceptance(config)
    assert callable(result)


@pytest.mark.unit
def test_make_acceptance_does_not_mutate_config():
    """
    make_acceptance must not attempt to mutate the frozen EnsembleConfig.
    (Mutation would raise FrozenInstanceError; we assert config fields
    are unchanged as a documentation guarantee.)
    """
    config = _make_config(pop_tolerance=0.12)
    make_acceptance(config)
    assert config.pop_tolerance == 0.12
