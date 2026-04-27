"""Tests for src.analysis.grc.config."""
import pytest

from src.analysis.grc.config import (
    DistrictType,
    GRCConfig,
    SG2025_DISTRICT_TYPES,
)


class TestDistrictType:
    def test_valid(self):
        dt = DistrictType(seat_count=4, num_districts=8)
        assert dt.seat_count == 4
        assert dt.num_districts == 8

    def test_invalid_seat_count(self):
        with pytest.raises(ValueError):
            DistrictType(seat_count=0, num_districts=5)

    def test_invalid_num_districts(self):
        with pytest.raises(ValueError):
            DistrictType(seat_count=1, num_districts=-1)


class TestGRCConfig:
    def test_sg2025_structure(self):
        cfg = GRCConfig()
        assert cfg.k_districts == 33
        assert cfg.total_seats == 97

    def test_seat_count_vector_length(self):
        cfg = GRCConfig()
        vec = cfg.seat_count_vector()
        assert len(vec) == cfg.k_districts

    def test_seat_count_vector_order(self):
        cfg = GRCConfig()
        vec = cfg.seat_count_vector()
        # First 15 are SMC (1 seat)
        assert vec[:15] == [1] * 15
        # Next 8 are 4-seat GRC
        assert vec[15:23] == [4] * 8
        # Last 10 are 5-seat GRC
        assert vec[23:] == [5] * 10

    def test_seat_counts_by_id(self):
        cfg = GRCConfig()
        seat_map = cfg.seat_counts_by_id()
        assert len(seat_map) == 33
        assert seat_map[0] == 1
        assert seat_map[14] == 1
        assert seat_map[15] == 4
        assert seat_map[22] == 4
        assert seat_map[23] == 5
        assert seat_map[32] == 5

    def test_from_seat_vector(self):
        vec = [1] * 15 + [4] * 8 + [5] * 10
        cfg = GRCConfig.from_seat_vector(vec, seed=123)
        assert cfg.k_districts == 33
        assert cfg.total_seats == 97
        assert cfg.seed == 123

    def test_sg2025_constants(self):
        smc = next(dt for dt in SG2025_DISTRICT_TYPES if dt.seat_count == 1)
        assert smc.num_districts == 15
        grc4 = next(dt for dt in SG2025_DISTRICT_TYPES if dt.seat_count == 4)
        assert grc4.num_districts == 8
        grc5 = next(dt for dt in SG2025_DISTRICT_TYPES if dt.seat_count == 5)
        assert grc5.num_districts == 10
