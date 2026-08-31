import importlib


def test_simulate_returns_nonnegative_reproducible_summary():
    mod = importlib.import_module('simulate_community')
    a = mod.run_experiment(seed=7, species=4, years=20)
    b = mod.run_experiment(seed=7, species=4, years=20)
    assert a['final_total_biomass'] >= 0
    assert a['final_total_biomass'] == b['final_total_biomass']

