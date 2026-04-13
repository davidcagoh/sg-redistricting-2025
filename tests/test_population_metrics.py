from __future__ import annotations

import pytest

from src.analysis.metrics.population import (
    compute_population_metrics,
    max_abs_deviation,
    population_deviation,
    population_range,
)


# ---------------------------------------------------------------------------
# population_deviation
# ---------------------------------------------------------------------------


class TestPopulationDeviation:
    def test_basic_over_and_under(self) -> None:
        result = population_deviation({0: 1100, 1: 900}, ideal=1000.0)
        assert result == pytest.approx({0: 0.1, 1: -0.1})

    def test_all_equal_to_ideal(self) -> None:
        result = population_deviation({0: 500, 1: 500, 2: 500}, ideal=500.0)
        assert result == pytest.approx({0: 0.0, 1: 0.0, 2: 0.0})

    def test_single_district_above_ideal(self) -> None:
        result = population_deviation({0: 1500}, ideal=1000.0)
        assert result == pytest.approx({0: 0.5})

    def test_single_district_below_ideal(self) -> None:
        result = population_deviation({0: 800}, ideal=1000.0)
        assert result == pytest.approx({0: -0.2})

    def test_three_districts_mixed(self) -> None:
        result = population_deviation({0: 1100, 1: 1000, 2: 900}, ideal=1000.0)
        assert result == pytest.approx({0: 0.1, 1: 0.0, 2: -0.1})

    def test_returns_new_dict_not_mutation(self) -> None:
        parts = {0: 1100, 1: 900}
        result = population_deviation(parts, ideal=1000.0)
        assert result is not parts

    def test_large_deviation(self) -> None:
        result = population_deviation({0: 2000, 1: 0}, ideal=1000.0)
        assert result == pytest.approx({0: 1.0, 1: -1.0})

    def test_non_integer_keys(self) -> None:
        result = population_deviation({5: 1100, 7: 900}, ideal=1000.0)
        assert result == pytest.approx({5: 0.1, 7: -0.1})


# ---------------------------------------------------------------------------
# max_abs_deviation
# ---------------------------------------------------------------------------


class TestMaxAbsDeviation:
    def test_basic(self) -> None:
        result = max_abs_deviation({0: 1100, 1: 900}, ideal=1000.0)
        assert result == pytest.approx(0.1)

    def test_single_district_equal_to_ideal(self) -> None:
        result = max_abs_deviation({0: 1000}, ideal=1000.0)
        assert result == pytest.approx(0.0)

    def test_all_equal_to_ideal(self) -> None:
        result = max_abs_deviation({0: 500, 1: 500, 2: 500}, ideal=500.0)
        assert result == pytest.approx(0.0)

    def test_picks_largest_absolute_value(self) -> None:
        # district 0 is -0.2, district 1 is +0.1 — max abs is 0.2
        result = max_abs_deviation({0: 800, 1: 1100}, ideal=1000.0)
        assert result == pytest.approx(0.2)

    def test_symmetric_deviations(self) -> None:
        result = max_abs_deviation({0: 1200, 1: 800}, ideal=1000.0)
        assert result == pytest.approx(0.2)

    def test_three_districts(self) -> None:
        result = max_abs_deviation({0: 1300, 1: 1000, 2: 900}, ideal=1000.0)
        assert result == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# population_range
# ---------------------------------------------------------------------------


class TestPopulationRange:
    def test_basic(self) -> None:
        result = population_range({0: 1200, 1: 800}, ideal=1000.0)
        assert result == pytest.approx(0.4)

    def test_uniform_population(self) -> None:
        result = population_range({0: 1000, 1: 1000, 2: 1000}, ideal=1000.0)
        assert result == pytest.approx(0.0)

    def test_single_district(self) -> None:
        result = population_range({0: 1500}, ideal=1000.0)
        assert result == pytest.approx(0.0)

    def test_three_districts(self) -> None:
        # max=1300, min=700, range/ideal = 600/1000
        result = population_range({0: 1300, 1: 1000, 2: 700}, ideal=1000.0)
        assert result == pytest.approx(0.6)

    def test_large_spread(self) -> None:
        result = population_range({0: 2000, 1: 0}, ideal=1000.0)
        assert result == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# compute_population_metrics
# ---------------------------------------------------------------------------


class TestComputePopulationMetrics:
    def test_basic_two_districts(self) -> None:
        result = compute_population_metrics({0: 1100, 1: 900})
        assert result["ideal_pop"] == pytest.approx(1000.0)
        assert result["max_abs_pop_dev"] == pytest.approx(0.1)
        assert result["pop_range"] == pytest.approx(0.2)

    def test_all_equal(self) -> None:
        result = compute_population_metrics({0: 500, 1: 500, 2: 500})
        assert result["ideal_pop"] == pytest.approx(500.0)
        assert result["max_abs_pop_dev"] == pytest.approx(0.0)
        assert result["pop_range"] == pytest.approx(0.0)

    def test_returns_required_keys(self) -> None:
        result = compute_population_metrics({0: 1100, 1: 900})
        assert "max_abs_pop_dev" in result
        assert "pop_range" in result
        assert "ideal_pop" in result

    def test_single_district(self) -> None:
        result = compute_population_metrics({0: 1234})
        assert result["ideal_pop"] == pytest.approx(1234.0)
        assert result["max_abs_pop_dev"] == pytest.approx(0.0)
        assert result["pop_range"] == pytest.approx(0.0)

    def test_three_unequal_districts(self) -> None:
        # total=3300, ideal=1100
        # deviations: 0→0/1100=0, 1→200/1100≈0.1818, 2→-200/1100≈-0.1818
        result = compute_population_metrics({0: 1100, 1: 1300, 2: 900})
        assert result["ideal_pop"] == pytest.approx(1100.0)
        assert result["max_abs_pop_dev"] == pytest.approx(200 / 1100)
        assert result["pop_range"] == pytest.approx(400 / 1100)

    def test_returns_float_values(self) -> None:
        result = compute_population_metrics({0: 1100, 1: 900})
        for key in ("max_abs_pop_dev", "pop_range", "ideal_pop"):
            assert isinstance(result[key], float)


# ---------------------------------------------------------------------------
# Edge cases: empty dict raises ValueError
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_dict_raises_value_error_compute(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            compute_population_metrics({})

    def test_empty_dict_raises_value_error_population_range(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            population_range({}, ideal=1000.0)

    def test_empty_dict_raises_value_error_max_abs_deviation(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            max_abs_deviation({}, ideal=1000.0)

    def test_empty_dict_raises_value_error_population_deviation(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            population_deviation({}, ideal=1000.0)
