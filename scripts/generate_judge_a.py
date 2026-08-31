"""Generate blind Judge A (mathematical rigor/assumptions) records from package evidence."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLIND = ROOT / "results" / "blind-submissions"
OUT = BLIND / "judge-records"
DIM = ["problem_understanding","model_reasonableness","mathematical_rigor","data_handling",
       "code_and_solving","model_validation","innovation","result_interpretation",
       "paper_quality","reproducibility"]
# Scores are conservative, evidence-based reviews on the registered 100-point rubric.
SCORES = {
1:[9,17,9,7,9,10,6,6,8,5],2:[9,16,8,6,9,9,5,6,8,5],3:[10,18,10,8,10,11,7,7,9,5],
4:[9,6,4,2,7,2,2,3,6,4],5:[9,5,4,2,6,2,2,3,4,3],6:[9,12,7,3,7,3,5,4,8,4],
7:[9,11,6,2,8,5,4,4,8,4],8:[7,8,4,2,7,3,2,3,5,4],9:[8,10,5,2,7,3,3,4,6,4],
10:[9,13,7,3,8,5,5,5,8,4],11:[6,5,3,1,5,1,1,2,3,2],12:[6,5,3,1,6,2,1,2,3,3],
13:[6,7,4,1,6,2,1,2,3,3],14:[5,4,2,1,5,1,1,1,2,2],15:[9,8,5,2,7,2,3,4,8,4],
16:[7,5,3,1,5,1,1,2,5,3],17:[8,10,5,2,8,4,3,4,6,4],18:[8,9,5,1,7,3,3,4,7,4],
19:[8,10,6,1,7,3,4,4,7,4],20:[8,11,6,2,8,5,4,4,7,4],21:[9,13,7,1,8,6,5,5,8,4],
22:[9,14,8,2,9,8,5,6,8,5],23:[9,14,8,7,9,8,5,6,8,4],24:[8,13,7,7,8,7,4,5,7,3],
25:[9,16,9,7,9,10,6,6,8,5],
}
NOTES = {
1:"Report states compositional closure, artifact-level validation, candidate models and permutation/CV diagnostics; metrics and figures are present.",
2:"Report gives composition assumptions and alternatives with LOOCV/figures; some empirical counts differ from other packages but are internally documented.",
3:"Detailed mathematical framing, CLR treatment, formulas, CV and permutation evidence; strongest explicit derivation among packages.",
4:"SDG framing is clear, but metrics use uniform weights/data_rows=0 and manifest lists major pending stages; quantitative network model is incomplete.",
5:"Problem framing and a uniform-baseline metric are documented, but no modeling report and no empirical data; most requested analyses pending.",
6:"Explicit risk formula, assumptions, falsification and limitations; location data absent and calibration/application explicitly pending.",
7:"Dynamic equations and scenario assumptions are stated and synthetic nature disclosed; no empirical data, so calibration/validation is limited.",
8:"Partial synthetic portfolio model with explicit data limitation; limited derivation and pending stages reduce rigor.",
9:"Policy simulation and robustness/falsification are reported, but input has no rows and several requested stages remain pending.",
10:"Extensive report with equations, Monte Carlo/robustness and figures; data status and scenario nature are disclosed.",
11:"Artifacts contain figures/metrics but no modeling report; assumptions and mathematical evidence are largely absent.",
12:"Code/test artifacts and figures exist, but no report and limited visible mathematical justification.",
13:"Short report/artifacts provide minimal evidence; no complete derivation or validation narrative.",
14:"Only a small artifact set and metrics/test evidence; problem understanding and assumptions are not sufficiently documented.",
15:"Long SDG report and metrics with explicit pending stages; relationship data absent, so ranking/forecast claims are incomplete.",
16:"Report acknowledges absent SDG data and pending stages; only one figure and sparse quantitative evidence.",
17:"Light-pollution model includes formula, intervention scenarios and sensitivity, while empirical rows are unavailable.",
18:"Structured light-pollution analysis with explicit input mode, validation limits and pending stages; no observations.",
19:"Auditable weighted risk formula and intervention assumptions; empirical location scores/calibration explicitly null.",
20:"Mechanistic drought equations, sweeps and reproducibility manifest are present; all parameters are hypothetical due to no data.",
21:"Detailed ecological equations, falsification and sensitivity; no empirical rows and conclusions are appropriately limited.",
22:"Coupled stock-flow and 243-scenario robust optimization with Pareto/ranking metrics and reproducibility manifest.",
23:"Wordle data audit, normalization assumptions, multiple questions and figures are evidenced; report file is absent.",
24:"Sailboat data audit, candidate models and quantitative metrics are present; report file absent but assumptions are clear in metrics.",
25:"Complete data audit, enhanced-vs-baseline CV, region effects, sensitivity and reproducibility are documented.",
}
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((BLIND/"manifest.json").read_text(encoding="utf-8"))
    ids = [p["submission_id"] for p in manifest["packages"]]
    for sid in ids:
        n = int(sid.split("-")[1]); vals = SCORES[n]
        rec = {"submission_id":sid,"judge_id":"A", "scores":dict(zip(DIM, vals)),
               "fatal_flags":[], "notes":NOTES.get(n, "Scores based only on package artifacts; missing evidence scored conservatively.")}
        (OUT/f"judge-A-{n:03d}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"generated {len(ids)} Judge A records")
if __name__ == "__main__": main()
