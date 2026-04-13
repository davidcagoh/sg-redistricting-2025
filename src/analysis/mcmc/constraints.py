"""
Constraint builders for the GerryChain ReCom MCMC chain.

GerryChain constraint callables have the signature:
    (partition: Partition) -> bool

``build_constraints`` returns a list of two callables:

1. ``gerrychain.constraints.contiguous`` — hard contiguity requirement.
   This is a plain function that checks all affected parts are connected.

2. A ``functools.partial`` wrapping
   ``gerrychain.constraints.within_percent_of_ideal_population``
   with ``percent`` bound to ``config.pop_tolerance``.

   Because ``within_percent_of_ideal_population`` needs an *initial partition*
   to compute the ideal population target, the partial in slot [1] must be
   called with ``(initial_partition)`` to obtain the ready-to-use ``Bounds``
   object before the chain starts.  The chain runner (in runner.py) is
   responsible for that two-step instantiation:

       pop_balance = constraints[1](initial_partition)
       validator   = Validator([constraints[0], pop_balance])
"""
from __future__ import annotations

import functools

from gerrychain.constraints import contiguous, within_percent_of_ideal_population

from src.analysis.config import EnsembleConfig


def build_constraints(config: EnsembleConfig) -> list:
    """Build the GerryChain constraint list for a ReCom chain.

    Returns a list containing:

    * ``constraints[0]`` — ``gerrychain.constraints.contiguous``, callable
      directly as ``contiguous(partition) -> bool``.

    * ``constraints[1]`` — ``functools.partial(within_percent_of_ideal_population,
      percent=config.pop_tolerance)``, callable as
      ``constraints[1](initial_partition) -> Bounds``.

    The caller must materialise the population ``Bounds`` by invoking
    ``constraints[1](initial_partition)`` and then pass both the contiguity
    function and the resulting ``Bounds`` into a ``Validator``.

    Args:
        config: Frozen ensemble configuration.  Only ``pop_tolerance`` is read;
                ``config`` is never mutated.

    Returns:
        A list ``[contiguous, pop_constraint_partial]``.
    """
    pop_constraint = functools.partial(
        within_percent_of_ideal_population,
        percent=config.pop_tolerance,
    )
    return [contiguous, pop_constraint]
