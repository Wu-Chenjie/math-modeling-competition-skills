# Math Modeling Skills Baseline Research Design

## Goal

在空工作区建立 `math-modeling-competition-skills/`，先完成融合架构前的基线研究：候选清单、Matt Pocock Skill 分析、数学建模 Skill 分析、差距分析和 A/B Benchmark 计划。

## Scope

- 本阶段研究公开仓库和公开文档，不复制第三方实现。
- 记录 GitHub API 元数据、检索日期、默认分支、目录证据和固定链接。
- 选择至少三个数学建模相关候选，并把相邻的 agent 产品单独标记，避免把“应用”误当成“Skill”。
- 不创建融合 Skill、不声称 Benchmark 已完成、不生成虚构实验结果。

## Evidence Model

每个判断分为：`Observed`（文件或 API 直接观察）、`Inferred`（基于观察的分析）、`Unverified`（缺少可重复证据）。Stars、Forks 和更新时间只用于检索优先级，不直接决定质量。

## Deliverables

1. `CANDIDATES.md`
2. `MATT_ANALYSIS.md`
3. `MATH_MODELING_ANALYSIS.md`
4. `GAP_ANALYSIS.md`
5. `BASELINE_BENCHMARK_PLAN.md`

## Quality Gates

- 每个关键结论至少绑定一个公开 URL 和文件/目录证据。
- 文档区分事实、推断、风险和待验证项。
- Benchmark 计划定义相同模型、题目、数据、预算、运行次数和程序化指标，但不伪造分数。
- 交付前执行链接、必需章节、元数据字段和 Markdown 结构检查。

## Next Gate

只有用户确认研究产物且证据检查通过，才进入 `ARCHITECTURE_PROPOSAL.md` 与 Skill 设计；若基线显示某个现有方案更稳健，后续设计必须保留该结论。
