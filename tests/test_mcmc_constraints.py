"""
Tests for src/analysis/mcmc/constraints.py — RED phase.

build_constraints(config) must return a list of callables that GerryChain's
ReCom chain can use. The list contains:

  [0] contiguous      — gerrychain.constraints.contiguous (partition -> bool)
  [1] pop_constraint  — functools.partial wrapping
                        within_percent_of_ideal_population with the tolerance
                        from config; callable with (initial_partition) -> Bounds

We use a lightweight mock for Partition objects so the tests have no
filesystem dependency.
"""
from __future__ import annotations

import functools
from unittest.mock import MagicMock, patch

import pytest

from src.analysis.config import EnsembleConfig
from src.analysis.mcmc.constraints import build_constraints


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs) -> EnsembleConfig:
    """Return an EnsembleConfig with sensible defaults, overriding via kwargs."""
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
# Return-type / structure tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_constraints_returns_list():
    config = _make_config()
    result = build_constraints(config)
    assert isinstance(result, list), "build_constraints must return a list"


@pytest.mark.unit
def test_build_constraints_has_at_least_two_elements():
    config = _make_config()
    result = build_constraints(config)
    assert len(result) >= 2, (
        "build_constraints must return at least 2 elements "
        "(contiguity + population balance)"
    )


@pytest.mark.unit
def test_build_constraints_all_elements_callable():
    config = _make_config()
    for i, item in enumerate(build_constraints(config)):
        assert callable(item), (
            f"Element {i} of the constraint list must be callable, got {type(item)}"
        )


# ---------------------------------------------------------------------------
# First element: contiguity
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_first_constraint_is_contiguous_function():
    """The first entry must be gerrychain.constraints.contiguous itself."""
    from gerrychain.constraints import contiguous

    config = _make_config()
    result = build_constraints(config)
    assert result[0] is contiguous, (
        "First constraint must be gerrychain.constraints.contiguous"
    )


# ---------------------------------------------------------------------------
# Second element: population balance — partial/closure using config.pop_tolerance
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_second_constraint_uses_config_tolerance():
    """
    The second element must encode config.pop_tolerance.

    We verify this by inspecting functools.partial keywords or by checking
    that different tolerances produce different objects whose keywords differ.
    """
    config_10 = _make_config(pop_tolerance=0.10)
    config_05 = _make_config(pop_tolerance=0.05)

    constraints_10 = build_constraints(config_10)
    constraints_05 = build_constraints(config_05)

    pop_c_10 = constraints_10[1]
    pop_c_05 = constraints_05[1]

    # If they are functools.partial objects, inspect keywords directly.
    if isinstance(pop_c_10, functools.partial) and isinstance(pop_c_05, functools.partial):
        kw_10 = pop_c_10.keywords
        kw_05 = pop_c_05.keywords
        # One of percent / pop_tolerance must differ between the two
        assert kw_10 != kw_05, (
            "Population constraint partials must differ when pop_tolerance differs"
        )
    else:
        # Callable wrapping: just ensure the two objects are distinct instances
        # (different tolerances → different closures)
        assert pop_c_10 is not pop_c_05, (
            "Population constraints for different tolerances must be distinct callables"
        )


@pytest.mark.unit
def test_second_constraint_callable_with_initial_partition():
    """
    Calling the second element with a mock initial_partition must not raise
    (duck-type check that the interface is correct).
    """
    from gerrychain.constraints import within_percent_of_ideal_population

    config = _make_config(pop_tolerance=0.10)
    constraints = build_constraints(config)
    pop_constraint = constraints[1]

    # Build a minimal mock partition that satisfies within_percent_of_ideal_population:
    # it needs partition["population"].values() and .keys()
    mock_partition = MagicMock()
    pop_data = {0: 1000, 1: 1000, 2: 1000, 3: 1000, 4: 1000}
    mock_partition.__getitem__ = MagicMock(return_value=pop_data)

    # Calling with a mock partition should return a Bounds (or similar callable),
    # i.e. it must not raise TypeError / AttributeError.
    try:
        result = pop_constraint(mock_partition)
    except Exception as exc:
        pytest.fail(
            f"Calling the population constraint with a mock partition raised {exc!r}"
        )

    assert callable(result), (
        "Calling the population constraint factory with a partition must return "
        "a callable Bounds object"
    )


# ---------------------------------------------------------------------------
# Contiguity constraint: mock a valid contiguous partition
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_contiguous_constraint_accepts_connected_partition():
    """
    The contiguous function from GerryChain should return True for a partition
    whose subgraphs are all connected. We mock the partition so no real graph
    is needed.
    """
    import networkx as nx
    from gerrychain.constraints import contiguous

    mock_partition = MagicMock()
    # affected_parts relies on partition.flips; mock a simple case where
    # contiguous checks two connected subgraphs.
    g1 = nx.path_graph(3)  # connected
    g2 = nx.path_graph(4)  # connected
    mock_partition.subgraphs = {0: g1, 1: g2}

    # Patch affected_parts to return the part keys we set up
    with patch(
        "gerrychain.constraints.contiguity.affected_parts",
        return_value=[0, 1],
    ):
        assert contiguous(mock_partition) is True


@pytest.mark.unit
def test_contiguous_constraint_rejects_disconnected_partition():
    """
    The contiguous function must return False when any subgraph is disconnected.
    """
    import networkx as nx
    from gerrychain.constraints import contiguous

    g_disconnected = nx.Graph()
    g_disconnected.add_nodes_from([0, 1, 2])
    # No edges → three isolated nodes → disconnected
    g_connected = nx.path_graph(3)

    mock_partition = MagicMock()
    mock_partition.subgraphs = {0: g_disconnected, 1: g_connected}

    with patch(
        "gerrychain.constraints.contiguity.affected_parts",
        return_value=[0, 1],
    ):
        assert contiguous(mock_partition) is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_build_constraints_zero_tolerance():
    """pop_tolerance=0.0 is a valid (strict) configuration."""
    config = _make_config(pop_tolerance=0.0)
    result = build_constraints(config)
    assert isinstance(result, list)
    assert len(result) >= 2
    assert all(callable(c) for c in result)


@pytest.mark.unit
def test_build_constraints_one_district():
    """k_districts=1 is a degenerate but valid configuration."""
    config = _make_config(k_districts=1)
    result = build_constraints(config)
    assert isinstance(result, list)
    assert len(result) >= 2


@pytest.mark.unit
def test_build_constraints_is_pure_no_mutation():
    """
    build_constraints must not mutate the config object (it is frozen, so this
    would raise FrozenInstanceError if attempted — but we assert the values
    are unchanged as a documentation test).
    """
    config = _make_config(pop_tolerance=0.07)
    build_constraints(config)
    assert config.pop_tolerance == 0.07
