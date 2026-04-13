from __future__ import annotations


def population_deviation(
    parts_pop: dict[int, int], ideal: float
) -> dict[int, float]:
    """Return {district_id: (pop - ideal) / ideal} for each district."""
    if not parts_pop:
        raise ValueError("parts_pop must not be empty")
    return {district: (pop - ideal) / ideal for district, pop in parts_pop.items()}


def max_abs_deviation(parts_pop: dict[int, int], ideal: float) -> float:
    """Return max(abs(deviation)) across all districts."""
    if not parts_pop:
        raise ValueError("parts_pop must not be empty")
    devs = population_deviation(parts_pop, ideal)
    return max(abs(d) for d in devs.values())


def population_range(parts_pop: dict[int, int], ideal: float) -> float:
    """Return (max_pop - min_pop) / ideal."""
    if not parts_pop:
        raise ValueError("parts_pop must not be empty")
    pops = list(parts_pop.values())
    return (max(pops) - min(pops)) / ideal


def compute_population_metrics(parts_pop: dict[int, int]) -> dict[str, float]:
    """Compute ideal population and deviation metrics for a partition.

    Returns:
        {
            "ideal_pop": float,
            "max_abs_pop_dev": float,
            "pop_range": float,
        }
    """
    if not parts_pop:
        raise ValueError("parts_pop must not be empty")
    ideal = sum(parts_pop.values()) / len(parts_pop)
    return {
        "ideal_pop": float(ideal),
        "max_abs_pop_dev": max_abs_deviation(parts_pop, ideal),
        "pop_range": population_range(parts_pop, ideal),
    }
