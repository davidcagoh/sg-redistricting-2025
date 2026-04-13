"""
Acceptance-function factories for the GerryChain ReCom MCMC chain.

We run a **uniform ensemble** — every proposed plan that satisfies the hard
constraints is accepted with probability 1.  This is the standard approach for
outlier analysis in redistricting research:

    "Under a uniform distribution over all valid plans, a plan that is an
     extreme outlier is strong evidence of intentional partisan manipulation."
     — Metric Geometry and Gerrymandering Group, GerryChain documentation

Using ``always_accept`` (Metropolis ratio ≡ 1) means the chain performs an
unweighted random walk over the feasible plan space.  A non-uniform target
distribution (e.g., tempered by partisan score) would bias the ensemble toward
plans that optimise a particular objective, which is *not* what we want for
impartial outlier detection.
"""
from __future__ import annotations

from gerrychain.accept import always_accept

from src.analysis.config import EnsembleConfig


def make_acceptance(config: EnsembleConfig):
    """Return the acceptance function for the MCMC chain.

    Always returns ``gerrychain.accept.always_accept`` because we run a
    uniform ensemble.  The ``config`` argument is accepted for API
    consistency with other factory functions in this module, but no fields
    of ``config`` are read.

    Args:
        config: Frozen ensemble configuration.  Not mutated; not read.

    Returns:
        ``gerrychain.accept.always_accept`` — a callable with signature
        ``(partition: Partition) -> bool`` that unconditionally returns
        ``True``.
    """
    # config is intentionally unused: the uniform ensemble does not require
    # any configuration knob.  We accept the argument so callers can treat
    # all factory functions in this module uniformly.
    _ = config
    return always_accept


def make_tempered_acceptance(beta: float):
    """Placeholder for a tempered acceptance function.

    Tempered acceptance (Metropolis–Hastings with a partisan-score energy
    function) is **not needed** for a uniform ensemble and is therefore
    not implemented.  If a future analysis requires a biased ensemble,
    implement this function and update the runner accordingly.

    Args:
        beta: Inverse temperature (higher → sharper peak around the
              energy minimum).

    Raises:
        NotImplementedError: Always — tempered acceptance is not needed for
            the current uniform ensemble design.
    """
    raise NotImplementedError(
        "make_tempered_acceptance is not implemented: the current pipeline "
        "uses a uniform ensemble (always_accept) and does not require a "
        "tempered or weighted acceptance function.  "
        f"Received beta={beta!r}."
    )
