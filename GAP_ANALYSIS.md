# Gap Analysis

Severity is based on expected impact on correctness or reproducibility, not document length. `Observed` evidence is linked; acceptance criteria are intended for the fusion architecture phase.

| ID | Severity | Gap | Evidence | Failure mode | Acceptance criterion |
|---|---|---|---|---|---|
| G01 | Critical | No shared, executed A/B benchmark across repositories | Public trees expose workflows but no neutral multi-case scorecard; see [XiaoMa](https://github.com/XiaoMaColtAI/math-modeling-skill), [zhnnky](https://github.com/zhnnky329/MathModeling-skills) | Architecture is selected by impression or Stars | Same harness runs Groups A/B/C on >=6 cases, >=3 seeds/runs, with raw artifacts and score distributions |
| G02 | Critical | No universal hard-fail policy for fabricated numbers, invalid code, leakage, or omitted constraints | Individual Skills mention verification, but no shared penalty ledger | Fluent but invalid submission receives high score | Programmatic checks and 10-30 point penalties; fatal errors block final score |
| G03 | Major | Candidate and baseline semantics differ | zhnnky defines a usable baseline; other flows do not expose one universal contract | Complex model appears better because baseline is non-comparable | Every scored case has a runnable baseline completing the same output and metric |
| G04 | Major | Validation is described more often than executed | Trees contain sensitivity/robustness references and scripts; execution evidence absent | Unsupported confidence and hidden overfit | Run logs include train/test or equivalent, residual/error, sensitivity, robustness and seed stability where applicable |
| G05 | Major | Reviewer independence and blind identity are not standardized | Review skills exist, but no cross-repository blind multi-judge protocol observed | Reviewer bias and author self-confirmation | Submissions renamed `Submission-###`; four judge outputs retained separately; disagreement flag computed |
| G06 | Major | State/artifact contracts are inconsistent | zhnnky has manifests; XiaoMa/Lupynow mostly role/file guidance | Chat memory loses assumptions, equations, or numbers | Canonical artifacts have schema, producer, consumer, status, hash and failure/backtrack fields |
| G07 | Major | Context loading can be too broad | XiaoMa and Lupynow root entrypoints are broad; references are large | Token cost rises and algorithm catalog pollutes decisions | Stage-local references; measure token/context size and require no unnecessary reference loads |
| G08 | Major | Model choice may be algorithm-first | Lupynow matrix/cookbook breadth; XiaoMa algorithm references | XGBoost/GA/AHP chosen from labels instead of structure | Method choice cites objective, constraints, data profile, baseline, risks, and fallback trigger |
| G09 | Major | Reproducibility evidence is not consistently machine-readable | XiaoMa has repro scripts; zhnnky specifies manifests; others vary | Results cannot be reconstructed or numbers drift into paper | Seed, input hashes, versions, command, runtime, parameters, outputs and figure hashes are recorded |
| G10 | Minor | Contest rules and template freshness need an explicit source gate | XiaoMa requires current official rules; other docs mix historical guidance | Wrong page/format or obsolete citation | Case metadata stores official rule URL/version and a pre-run rules check |
| G11 | Minor | Adjacent application systems confound Skill effects | MathModelAgent includes backend/frontend runtime | Product features are attributed to prompt architecture | Evaluate pure Skills and applications in separate tracks, report setup/runtime overhead |
| G12 | Minor | No regression protocol tied to Skill changes | Public repositories have versioned files but no shared before/after benchmark gate | Fixing one class degrades another silently | Every Skill change records before/after subset, regression threshold, token/runtime delta |

## Risk summary

The first five risks to resolve are G01, G02, G03, G04, and G05. They directly affect whether any later claim of superiority is falsifiable. G07 and G08 are the main efficiency and model-selection risks; G10-G12 can be addressed after the baseline harness exists.

