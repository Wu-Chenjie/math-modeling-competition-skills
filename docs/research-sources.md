# Research Sources Ledger

Retrieval date: 2026-08-30 (Asia/Shanghai)

| ID | Repository or source | URL | Retrieved | Evidence type | Notes |
|---|---|---|---|---|---|
| S01 | Matt Pocock Skills | https://github.com/mattpocock/skills | 2026-08-30 | Repository metadata and tree | Engineering Skill architecture |
| S02 | XiaoMaColtAI math-modeling-skill | https://github.com/XiaoMaColtAI/math-modeling-skill | 2026-08-30 | Repository metadata and tree | CUMCM/MCM/ICM workflow |
| S03 | zhnnky329 MathModeling-skills | https://github.com/zhnnky329/MathModeling-skills | 2026-08-30 | Repository metadata and tree | Candidate modeling Skill collection |
| S04 | Lupynow math-modeling-skills | https://github.com/Lupynow/math-modeling-skills | 2026-08-30 | Repository metadata and tree | Candidate modeling Skill collection |
| S05 | jihe520 MathModelAgent | https://github.com/jihe520/MathModelAgent | 2026-08-30 | Repository metadata and tree | Adjacent multi-agent product; not treated as a pure Skill |
| S06 | GitHub REST repository endpoint | https://api.github.com/repos/mattpocock/skills | 2026-08-30 | API metadata | Stars, forks, timestamps, branch, license |
| S07 | GitHub REST repository endpoint | https://api.github.com/repos/XiaoMaColtAI/math-modeling-skill | 2026-08-30 | API metadata | Stars, forks, timestamps, branch, license |
| S08 | GitHub REST repository endpoint | https://api.github.com/repos/zhnnky329/MathModeling-skills | 2026-08-30 | API metadata | Stars, forks, timestamps, branch, license |
| S09 | GitHub REST repository endpoint | https://api.github.com/repos/Lupynow/math-modeling-skills | 2026-08-30 | API metadata | Stars, forks, timestamps, branch, license |
| S10 | GitHub REST repository endpoint | https://api.github.com/repos/jihe520/MathModelAgent | 2026-08-30 | API metadata | Stars, forks, timestamps, branch, license |

## Reproducible query method

For each repository, query `GET https://api.github.com/repos/{owner}/{repo}` and `GET https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1`. Inspect only files returned by the tree endpoint; use the repository's raw URL at the recorded default branch for content.

## Phase gate record

- Current finding: focused routing/state artifacts are more directly testable than monolithic prompts.
- Evidence: zhnnky exposes parser/auditor/selector/orchestrator files and explicit gate contracts; XiaoMa and Lupynow expose broad domain references and templates.
- Rejected assumption: popularity is a proxy for correctness.
- Risks: metadata changes over time; public repository presence does not prove runtime execution; `jihe520/MathModelAgent` includes application infrastructure and needs a separate track.
- Required modification before Architecture Design: select the primary A baseline by evidence, create the historical case manifest, and pre-register controlled conditions and hard penalties.
- Next-stage rationale: only a fair A/B run can test whether engineering architecture improves outcomes beyond domain breadth.
