"""
Task 0.3 — Import smoke tests.

Written FIRST (TDD Red phase). Tests for the analysis subpackages will fail
until the scaffold (src/analysis/...) is created.
"""


def test_geopandas_importable():
    import geopandas

    assert geopandas.__version__


def test_gerrychain_importable():
    import gerrychain
    from gerrychain import Graph, MarkovChain, Partition
    from gerrychain.proposals import recom

    assert gerrychain.__version__


def test_pyarrow_importable():
    import pyarrow

    assert pyarrow.__version__


def test_typer_importable():
    import typer

    assert typer.__version__


def test_analysis_package_importable():
    from src import analysis  # noqa


def test_analysis_subpackages_importable():
    from src.analysis import mcmc, metrics, reporting  # noqa
