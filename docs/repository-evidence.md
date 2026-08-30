# Repository Evidence

Retrieval date: 2026-08-30 (Asia/Shanghai). Metadata was queried from the GitHub REST API; tree and content claims refer to the default branch shown below.

| Repository | Stars | Forks | Updated | Pushed | Branch | License | Size | Primary language | Direct evidence |
|---|---:|---:|---|---|---|---|---:|---|---|
| `mattpocock/skills` | 241,093 | 20,507 | 2026-08-30 | 2026-08-24 | `main` | MIT | 1,548 KB | Shell | [API](https://api.github.com/repos/mattpocock/skills), [tree](https://github.com/mattpocock/skills/tree/main/skills) |
| `XiaoMaColtAI/math-modeling-skill` | 953 | 58 | 2026-08-30 | 2026-08-29 | `main` | Unverified (API returned null) | 69,678 KB | Python | [API](https://api.github.com/repos/XiaoMaColtAI/math-modeling-skill), [SKILL](https://raw.githubusercontent.com/XiaoMaColtAI/math-modeling-skill/main/SKILL.md) |
| `zhnnky329/MathModeling-skills` | 649 | 29 | 2026-08-30 | 2026-08-24 | `main` | MIT | 657 KB | Shell | [API](https://api.github.com/repos/zhnnky329/MathModeling-skills), [skills](https://github.com/zhnnky329/MathModeling-skills/tree/main/.codex/skills) |
| `Lupynow/math-modeling-skills` | 273 | 9 | 2026-08-29 | 2026-07-31 | `main` | MIT | 658 KB | Python | [API](https://api.github.com/repos/Lupynow/math-modeling-skills), [skills](https://github.com/Lupynow/math-modeling-skills/tree/main/skills) |
| `jihe520/MathModelAgent` | 3,905 | 356 | 2026-08-30 | 2026-08-27 | `main` | Unverified (API returned null) | 99,685 KB | Python | [API](https://api.github.com/repos/jihe520/MathModelAgent), [skills](https://github.com/jihe520/MathModelAgent/tree/main/skills) |

## Observed architecture evidence

### Matt Pocock Skills

`skills/engineering/` contains separate `code-review`, `domain-modeling`, `grill-with-docs`, `implement`, `prototype`, `research`, `tdd`, and `to-spec` entrypoints. The repository README describes the set as small, composable, editable skills and distinguishes user-invoked orchestration from model-invoked reusable discipline. This is evidence for an engineering process architecture, not mathematical domain competence.

### XiaoMaColtAI/math-modeling-skill

The root `SKILL.md` defines modeling, programming, and paper roles; its tree includes seven algorithm references, role-specific references, Python/MATLAB checks, figure/document/LaTeX/PDF/XLSX tools, templates, and reproducibility scripts. The root instructions require stage gates and prohibit fabricated results. Observed depth is high, but the main entrypoint is roughly 10 KB and loads a broad workflow before conditional references; context cost and independent benchmark evidence remain unverified.

### zhnnky329/MathModeling-skills

The `.codex/skills` tree contains focused components: `problem-parser`, `data-auditor-cleaner`, `method-selector`, `workflow-orchestrator`, `model-assumptions-builder`, language-specific code generators/reviewers, `robustness-checker`, `consistency-auditor`, and `quality-assurance-auditor`. The orchestrator contract defines G1-G6 gates, canonical manifests, human method choice, change-impact routing, and lean/submission profiles. This is strong evidence of explicit state and routing design; execution results are not supplied by the repository snapshot.

### Lupynow/math-modeling-skills

The tree separates `math-modeling-solver` and `math-modeling-paper`, with model-selection matrices, eight cookbooks, problem playbooks, MCM guidance, paper references, and Python/MATLAB templates covering optimization, evaluation, mechanistic, network, statistical, machine-learning, and clustering families. This is strong breadth and reference organization; the root solver is a large, instruction-heavy entrypoint and no independent contest benchmark was observed.

### jihe520/MathModelAgent

The tree includes a backend/frontend application plus `1start-mathmodel`, `2analysis-modeling`, `3coding-visual`, `4drawio`, and `5writing` skills. It provides Chinese/English paper templates and an end-to-end product workflow. It should be evaluated as an adjacent multi-agent application, not as a pure Skill bundle, because runtime behavior depends on application code and services.

## Evidence limits

- GitHub metadata is time-sensitive and must be re-sampled before a final release decision.
- Repository claims are not equivalent to successful execution. No benchmark score, hallucination rate, reproducibility rate, or reviewer agreement is asserted here.
- A missing license in API metadata is recorded as `Unverified`, not inferred from repository conventions.

