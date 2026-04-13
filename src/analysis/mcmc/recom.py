"""ReCom MCMC chain construction for the Singapore electoral redistricting pipeline.

Provides two factory functions:

- :func:`build_initial_partition` — wraps a networkx graph in a GerryChain
  Partition with a ``"population"`` Tally updater wired to the ``pop_total``
  node attribute.

- :func:`build_chain` — constructs a GerryChain MarkovChain using the ReCom
  proposal, caller-supplied constraints, and an acceptance function.
"""
from __future__ import annotations

import functools
from typing import Any, Callable, Iterable

import networkx as nx
from gerrychain import Graph as GCGraph
from gerrychain import MarkovChain, Partition
from gerrychain.proposals import recom
from gerrychain.updaters import Tally

from src.analysis.config import EnsembleConfig

# Name used for the population Tally updater throughout the pipeline.
_POP_UPDATER_KEY = "population"


def build_initial_partition(
    graph: nx.Graph,
    assignment: dict[int, int],
    config: EnsembleConfig,
) -> Partition:
    """Build a GerryChain Partition from a seed assignment.

    Wraps *graph* (a plain ``networkx.Graph``) in a ``gerrychain.Graph`` so that
    GerryChain's internals can operate on it, then constructs a
    :class:`gerrychain.Partition` with a single ``"population"`` updater that
    tallies the ``pop_total`` node attribute across each district.

    Parameters
    ----------
    graph:
        Adjacency graph produced by the subzone graph builder.  Each node must
        carry a ``pop_total`` integer attribute.
    assignment:
        Mapping of ``node_id → district_id`` representing the seed partition.
    config:
        Ensemble configuration (used here only to make the signature uniform;
        future callers may need ``k_districts`` from it).

    Returns
    -------
    gerrychain.Partition
        A freshly constructed partition ready to serve as the initial state of
        a :class:`gerrychain.MarkovChain`.
    """
    gc_graph = GCGraph(graph)
    updaters: dict[str, Any] = {
        _POP_UPDATER_KEY: Tally("pop_total", alias=_POP_UPDATER_KEY),
    }
    return Partition(
        graph=gc_graph,
        assignment=assignment,
        updaters=updaters,
    )


def build_chain(
    initial_partition: Partition,
    config: EnsembleConfig,
    constraints: Iterable[Callable],
    acceptance: Callable,
) -> MarkovChain:
    """Build a GerryChain MarkovChain for ReCom.

    The ideal population target is derived from the ``"population"`` updater on
    *initial_partition* so that the chain targets perfect proportional balance.

    Parameters
    ----------
    initial_partition:
        Starting state returned by :func:`build_initial_partition`.
    config:
        Ensemble configuration supplying ``n_steps``, ``recom_epsilon``, and
        ``recom_node_repeats``.
    constraints:
        An iterable of constraint callables passed directly to
        :class:`gerrychain.MarkovChain`.  Each must accept a
        :class:`gerrychain.Partition` and return a ``bool``.
    acceptance:
        Acceptance function passed to :class:`gerrychain.MarkovChain`.  In the
        simplest case this is ``gerrychain.accept.always_accept``.

    Returns
    -------
    gerrychain.MarkovChain
        A chain configured with ``config.n_steps`` total steps.
    """
    total_pop = sum(initial_partition[_POP_UPDATER_KEY].values())
    pop_target = total_pop / config.k_districts

    proposal = functools.partial(
        recom,
        pop_col="pop_total",
        pop_target=pop_target,
        epsilon=config.recom_epsilon,
        node_repeats=config.recom_node_repeats,
    )

    return MarkovChain(
        proposal=proposal,
        constraints=constraints,
        accept=acceptance,
        initial_state=initial_partition,
        total_steps=config.n_steps,
    )
