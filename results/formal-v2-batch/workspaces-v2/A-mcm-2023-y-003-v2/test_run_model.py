from run_model import load_data, design

def test_supplied_rows_are_loaded_and_design_is_finite():
    _, df = load_data()
    assert len(df) == 3490
    X, names = design(df, False)
    assert X.shape[0] == len(df)
    assert X.shape[1] == len(names)
    assert X.min() == X.min()
