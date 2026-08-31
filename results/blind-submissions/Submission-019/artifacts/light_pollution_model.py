"""Dependency-free light-pollution risk metric prototype."""

WEIGHTS = {
    "skyglow": 0.30,
    "trespass": 0.20,
    "glare": 0.15,
    "ecology": 0.20,
    "human": 0.15,
}

INTERVENTIONS = {
    "shielding": {"skyglow": 0.10, "trespass": 0.55, "glare": 0.45, "ecology": 0.05, "human": 0.05},
    "dimming": {"skyglow": 0.35, "trespass": 0.30, "glare": 0.25, "ecology": 0.10, "human": 0.20},
    "curfew": {"skyglow": 0.25, "trespass": 0.35, "glare": 0.30, "ecology": 0.40, "human": 0.35},
}


def _validate_components(components):
    missing = set(WEIGHTS) - set(components)
    if missing:
        raise ValueError(f"missing components: {sorted(missing)}")
    for name in WEIGHTS:
        value = components[name]
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be numeric in [0, 1]")


def score_risk(components):
    """Return a 0-100 weighted risk score from normalized component burdens."""
    _validate_components(components)
    return 100.0 * sum(WEIGHTS[name] * components[name] for name in WEIGHTS)


def risk_band(score):
    if score < 20:
        return "low"
    if score < 40:
        return "moderate"
    if score < 60:
        return "high"
    return "very_high"


def apply_intervention(components, intervention):
    """Apply an assumed fractional reduction vector; assumptions are not observations."""
    _validate_components(components)
    if intervention not in INTERVENTIONS:
        raise ValueError(f"unknown intervention: {intervention}")
    reductions = INTERVENTIONS[intervention]
    return {name: max(0.0, components[name] * (1.0 - reductions[name])) for name in WEIGHTS}


def rank_interventions(components):
    ranked = []
    for intervention in INTERVENTIONS:
        post = apply_intervention(components, intervention)
        ranked.append((intervention, score_risk(post)))
    return sorted(ranked, key=lambda item: (item[1], item[0]))
