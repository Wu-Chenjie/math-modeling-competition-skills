import math

from run_analysis import artifact_id, close, clr, inverse_clr


def test_artifact_id_removes_sampling_suffix():
    assert artifact_id("03部位2") == "03"


def test_closure_and_clr_respect_compositional_geometry():
    values = [0, 20, 30, 50]
    assert math.isclose(sum(close(values)), 100.0)
    transformed = clr(values)
    assert math.isclose(sum(transformed), 0.0, abs_tol=1e-12)
    assert all(v > 0 for v in inverse_clr(transformed))
    assert math.isclose(sum(inverse_clr(transformed)), 100.0)
