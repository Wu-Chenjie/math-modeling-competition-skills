import json
from pathlib import Path

import numpy as np


def test_load_and_validity_filter():
    import math_model_run as mm

    data = mm.load_case(mm.CASE_JSON)
    assert {"meta", "chem", "unknown", "components", "source"} == set(data)
    assert len(data["meta"]) == 58
    assert len(data["chem"]) == 69
    valid = [r for r in data["chem"] if r["valid"]]
    assert len(valid) > 40
    assert all(85 <= r["total"] <= 105 for r in valid)


def test_clr_and_centroid_classifier_shapes():
    import math_model_run as mm

    x = np.array([[50.0, 50.0], [25.0, 75.0]])
    z = mm.clr(x)
    assert z.shape == x.shape
    assert np.allclose(z.sum(axis=1), 0.0)
    pred, margin = mm.nearest_centroid(np.array([[0.0, 0.0]]), ["a", "b"], np.array([[0.0, 0.0], [1.0, 1.0]]))
    assert pred == ["a"]
    assert margin.shape == (1,)
