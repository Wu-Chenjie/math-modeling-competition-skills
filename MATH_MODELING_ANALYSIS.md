# Mathematical Modeling Skills Analysis

## Evidence basis

This analysis compares public entrypoints and supporting trees from [XiaoMaColtAI](https://raw.githubusercontent.com/XiaoMaColtAI/math-modeling-skill/main/SKILL.md), [zhnnky329](https://raw.githubusercontent.com/zhnnky329/MathModeling-skills/main/.codex/skills/workflow-orchestrator/SKILL.md), [Lupynow solver](https://raw.githubusercontent.com/Lupynow/math-modeling-skills/main/skills/math-modeling-solver/SKILL.md), [Lupynow paper](https://raw.githubusercontent.com/Lupynow/math-modeling-skills/main/skills/math-modeling-paper/SKILL.md), and [MathModelAgent analysis](https://raw.githubusercontent.com/jihe520/MathModelAgent/main/skills/2analysis-modeling/SKILL.md). Claims below are observed unless marked inferred.

| Capability | XiaoMaColtAI | zhnnky329 | Lupynow | MathModelAgent | Domain value vs prompt filler |
|---|---|---|---|---|---|
| Problem analysis | Three-stage modeling role; requires reading full problem and outputs structured analysis | Model-neutral parser extracts goals, objects, data, decisions, constraints, outputs, dependencies, ambiguities | Stage 1 classifies 12 problem natures and dependencies | Analysis report requires decomposition, data understanding, ambiguity pre-check | Structured extraction and ambiguity tests are domain/process value; “analyze carefully” alone is filler |
| Data audit | Data/code roles and check scripts observed, detail varies by role | Dedicated auditor checks schema, missingness, duplicates, units, outliers, leakage, coverage and readiness | EDA and data guidance in cookbooks/playbooks; reusable profile contract not clearly observed | Data understanding is required in analysis report | Explicit fields, units, hashes, leakage checks are professional value |
| Modeling | Seven algorithm reference families and role guidance | Method selector derives requirements from outputs, constraints, data and risk | Matrix/cookbooks/playbooks cover broad algorithm families | Analysis role maps variables, assumptions, objectives and constraints | Equations, feasibility, data need and risk are value; algorithm name lists are not decisions |
| Candidate generation | References offer many methods; minimum comparison policy not consistently visible | Main + usable baseline + optional fallback, with risk probes and human choice | At least two candidate models in solver flow; matrix recommendations can bias selection | Analysis usually proposes route after classification | Baseline and explicit trade-offs are value; fixed “use X” heuristics are filler |
| Baseline | Stage gates and verification language; baseline contract not clearly standardized | Baseline must complete real task and have comparable output | Baseline guidance exists but not a single gate contract | Baseline requirement varies by report | A runnable comparable baseline is high-value and testable |
| Validation | Sensitivity/robustness and subagent QA are required in places; independent measurement unverified | G3/G4 gates, risk probes, run summaries, robustness and auditors | Model-validation references and sensitivity guidance | Code stage validates constraints and outputs; independent execution unverified | Executed metrics and failure gates are value; prose promises are filler |
| Code execution | Python/MATLAB scripts, environment checks and artifact production observed | Generators/reviewers plus run summaries and reproducibility fields specified | Many templates are runnable in principle; actual runs unverified | Coding stage explicitly runs models and produces figures | Real execution logs and artifact checks are value |
| Paper | Dedicated role with Word/LaTeX templates and verified-result boundary | Writers consume frozen/canonical artifacts and auditors | Dedicated paper Skill and self-review framework | Writing consumes analysis/results/figures and templates | Result-to-paper traceability is value; generic prose advice is filler |
| Reviewer | QA/subagent checks and paper self-review; role independence varies | Separate consistency, completeness, QA, robustness and language reviews; gates block final | Self-review and validation references; multi-judge independence unverified | Review agents and report steps | Independent blind review plus hard penalties is a missing benchmark-level control |
| Reproducibility | Repro manifest/check scripts observed | Hashes, seeds, configs, manifests and run summaries specified | Templates/guidance, but uniform manifest unclear | Runtime reproducibility depends on app setup | Machine-readable provenance is value; “can rerun” without command/hash is filler |

## Observed professional knowledge

1. Mathematical modeling is a sequence of framing, data semantics, assumptions, candidate models, feasibility, computation, and validation; the strongest evidence is zhnnky's model-neutral parser and gate contracts.
2. Domain references are useful when conditional: Lupynow's cookbooks and playbooks expose equations, algorithm families and code templates, but they should inform rather than decide.
3. Contest paper production is downstream of verified results. XiaoMaColtAI, Lupynow, and MathModelAgent all encode a separation between analysis/code and paper artifacts, though the strength of numeric traceability varies.
4. Reproducibility requires more than fixed seeds: inputs, versions, parameters, commands, generated artifacts, and consistency checks must be captured.

## Prompt filler patterns

- Repeated imperatives such as “认真分析”“选择合适模型” without a required artifact or measurable gate.
- Long algorithm catalogs with no data-need, assumption, baseline, or fallback rule.
- Claims that a script is “可运行” without a run command, exit code, output file, or environment record.
- Paper templates that contain placeholders but no check that every reported number maps to results.

