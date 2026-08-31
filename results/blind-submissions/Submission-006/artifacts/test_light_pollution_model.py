import unittest

from light_pollution_model import (
    MetricInputError,
    compute_risk,
    intervention_effect,
    validate_location_record,
)


class LightPollutionMetricTests(unittest.TestCase):
    def test_risk_is_bounded_and_monotone_for_harm_indicators(self):
        low = compute_risk({
            "skyglow": 0.1, "trespass": 0.1, "glare": 0.1,
            "clutter": 0.1, "ecological_sensitivity": 0.1,
            "human_vulnerability": 0.1, "lighting_need": 0.9,
        })
        high = compute_risk({
            "skyglow": 0.9, "trespass": 0.9, "glare": 0.9,
            "clutter": 0.9, "ecological_sensitivity": 0.9,
            "human_vulnerability": 0.9, "lighting_need": 0.1,
        })
        self.assertGreaterEqual(low["risk_score"], 0.0)
        self.assertLessEqual(high["risk_score"], 100.0)
        self.assertGreater(high["risk_score"], low["risk_score"])

    def test_missing_location_record_is_rejected(self):
        with self.assertRaises(MetricInputError):
            validate_location_record({"skyglow": 0.5})

    def test_intervention_never_increases_a_reduced_exposure_component(self):
        location = {
            "skyglow": 0.8, "trespass": 0.7, "glare": 0.6,
            "clutter": 0.5, "ecological_sensitivity": 0.8,
            "human_vulnerability": 0.5, "lighting_need": 0.6,
        }
        after = intervention_effect(
            location,
            {"skyglow": 0.5, "trespass": 0.5, "glare": 0.5},
        )
        self.assertLessEqual(after["skyglow"], location["skyglow"])
        self.assertLessEqual(after["trespass"], location["trespass"])
        self.assertLessEqual(after["glare"], location["glare"])


if __name__ == "__main__":
    unittest.main()
