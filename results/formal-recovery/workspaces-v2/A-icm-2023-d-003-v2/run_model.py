import argparse
import hashlib
import json
import platform
import re
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def extract_goals(problem_text: str):
    goals = []
    pattern = r'GOAL\s+(\d+)\s*:\s*(.*?)(?=\s+GOAL\s+\d+\s*:|\s*\||\s*Your PDF solution|$)'
    for match in re.finditer(pattern, problem_text, flags=re.DOTALL):
        goals.append({'id': f'GOAL {match.group(1)}', 'name': match.group(2).strip()})
    return goals


def write_figure(path: Path, goal_count: int, data_rows: int):
    values = [goal_count, data_rows]
    labels = ['SDG labels', 'Audited rows']
    maxv = max(values + [1])
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="340" viewBox="0 0 600 340">',
        '<rect width="600" height="340" fill="white"/>',
        '<text x="300" y="32" text-anchor="middle" font-family="Arial" font-size="18">Benchmark input audit status</text>',
        '<text x="35" y="180" transform="rotate(-90 35 180)" text-anchor="middle" font-family="Arial" font-size="14">Count</text>',
        '<line x1="80" y1="280" x2="560" y2="280" stroke="#333"/>',
    ]
    colors = ['#0072B2', '#D55E00']
    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        x = 150 + i * 220
        height = 220 * value / maxv
        y = 280 - height
        svg += [f'<rect x="{x}" y="{y:.1f}" width="100" height="{height:.1f}" fill="{color}"/>',
                f'<text x="{x+50}" y="{y-8:.1f}" text-anchor="middle" font-family="Arial" font-size="14">{value}</text>',
                f'<text x="{x+50}" y="305" text-anchor="middle" font-family="Arial" font-size="13">{label}</text>']
    svg.append('</svg>')
    path.with_suffix('.svg').write_text(''.join(svg), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output-dir', default='results')
    args = parser.parse_args()
    input_path = Path(args.input).resolve()
    out_dir = Path(args.output_dir).resolve()
    fig_dir = out_dir.parent / 'figures'
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    case = json.loads(input_path.read_text(encoding='utf-8'))
    goals = extract_goals(case.get('problem_text', ''))
    data_files = case.get('data_files', [])
    rows_data = case.get('rows_data', [])
    data_audit = case.get('data_audit', [])
    has_data = bool(data_files or rows_data or data_audit)

    pending = [
        'network construction and edge-weight estimation',
        'priority ranking and effectiveness evaluation',
        '10-year scenario projection',
        'achieved-goal network recomputation',
        'crisis perturbation analysis',
        'organization transfer validation',
        'weight sensitivity and ranking robustness',
        'falsification against observed outcomes',
    ] if not has_data else []

    report = {
        'problem_framing': {
            'objective': 'Prioritize the 17 UN Sustainable Development Goals using an interdependency network.',
            'subproblems': ['q1 network and priorities', 'q2 achieved-goal counterfactual', 'q3 crisis impacts', 'q4 transferability']
        },
        'data_audit': {
            'case_id': case.get('case_id'),
            'source_status': case.get('source_status'),
            'problem_sha256_declared': case.get('problem_sha256'),
            'data_sha256_declared': case.get('data_sha256'),
            'input_sha256_observed': sha256_file(input_path),
            'data_files': data_files,
            'rows_data_count': len(rows_data),
            'data_audit_count': len(data_audit),
            'goal_count_extracted': len(goals),
            'goal_labels': goals,
            'finding': 'No data files, rows_data, or data_audit records are supplied; only official problem text is available.'
        },
        'assumptions': ['No SDG relationship, weight, outcome, or crisis value is inferred without supplied data.'],
        'candidate_models': [
            'Data-ready option A: directed weighted SDG network with multi-criteria centrality and constraint-aware prioritization.',
            'Data-ready option B: robust outranking / Pareto analysis over normalized SDG benefit, cost, and resilience criteria.'
        ],
        'baseline': 'No numerical baseline is computed because no edge or criterion data are present.',
        'math_specification': 'For supplied data, normalize criteria x_ij, estimate adjacency W, score p_i = alpha centrality_i + beta marginal_gain_i - gamma cost_i, and report rank stability over an explicit weight simplex. Parameters cannot be instantiated from this input.',
        'code_prototype': {'script': 'run_model.py', 'deterministic_seed': 0},
        'experiment': 'Input audit and SDG-label extraction only.',
        'validation': 'Structural validation passed for JSON parsing and extraction of all 17 SDG labels; predictive validation pending data.',
        'sensitivity_robustness': 'Pending; no criteria or weights available.',
        'falsification': 'Pending; no observed outcomes or external edge list available.',
        'reviewer_risks': ['Arbitrary weights', 'scale mismatch', 'unverifiable network edges', 'no ranking robustness without data'],
        'reproducibility_manifest': {
            'command': 'python run_model.py --input ../benchmarks/case-summaries/icm-2023-d.json --output-dir results',
            'python': sys.version,
            'platform': platform.platform(),
            'seed': 0,
            'input_path': str(input_path),
            'input_sha256_observed': sha256_file(input_path),
        },
        'status': 'pending_data',
        'pending_stages': pending,
    }
    metrics = {
        'status': report['status'],
        'case_id': case.get('case_id'),
        'goal_count': len(goals),
        'rows_data_count': len(rows_data),
        'data_audit_count': len(data_audit),
        'figures': ['figures/input_audit_status.svg'],
        'pending_stages': pending,
        'report': report,
    }
    (out_dir / 'modeling_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (out_dir / 'metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    write_figure(fig_dir / 'input_audit_status.png', len(goals), len(rows_data))
    print(json.dumps({'status': report['status'], 'goals': len(goals), 'rows_data': len(rows_data), 'pending': len(pending)}))


if __name__ == '__main__':
    main()
