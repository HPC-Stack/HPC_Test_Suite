#!/usr/bin/env python3
# Cross-compiler performance comparison.
# Run same benchmark across multiple environments and compare results.
#
# Usage:
#   python3 scripts/compare_compilers.py application/gromacs gromacs
#
# Runs the given benchmark path with tag across gnu, foss, intel envs,
# then prints a performance comparison table.

import json
import os
import subprocess
import sys
import tempfile

ENVIRONMENTS = ['gnu', 'foss', 'intel']
SYSTEMS = {
    'gnu':   'paramrudra.snbose:cpu',
    'foss':  'paramrudra.snbose:cpu',
    'intel': 'paramrudra.snbose:cpu',
}


def run_benchmark(path, tag, environ):
    '''Run reframe and return the report data.'''
    report = tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w')
    report.close()

    cmd = [
        'reframe', '-c', path, '-t', tag,
        '-S', f'valid_systems={SYSTEMS.get(environ, "*:cpu")}',
        '-S', f'valid_prog_environs={environ}',
        '--report-file', report.name,
        '-r',
    ]
    print(f'  [{environ}] Running: {" ".join(cmd[-8:])}')

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print(f'  [{environ}] TIMEOUT')
        return None

    if result.returncode != 0:
        print(f'  [{environ}] FAILED (exit={result.returncode})')
        for line in result.stderr.split('\n')[-5:]:
            if line.strip():
                print(f'    {line.strip()}')

    with open(report.name) as f:
        data = json.load(f)
    os.unlink(report.name)
    return data


def extract_perf_values(report_data):
    '''Extract performance values from a report.'''
    results = []
    for run in report_data.get('runs', []):
        for tc in run.get('testcases', []):
            entry = {
                'name': tc.get('display_name') or tc.get('name'),
                'result': tc.get('result'),
                'perf': dict(tc.get('perfvalues', {})),
                'time_run': tc.get('time_run'),
                'time_total': tc.get('time_total'),
                'partition': tc.get('partition'),
                'environ': tc.get('environ'),
                'fail_reason': tc.get('fail_reason'),
            }
            results.append(entry)
    return results


def print_table(all_results):
    '''Pretty-print a comparison table.'''
    # Group by test name
    groups = {}
    for env, results in all_results.items():
        for r in results:
            name = r['name']
            if name not in groups:
                groups[name] = {}
            groups[name][env] = r

    for name in sorted(groups):
        print(f'\n{"="*60}')
        print(f'  {name}')
        print(f'{"="*60}')
        envs = groups[name]

        # Header
        header = f'  {"Metric":<20}'
        for e in ENVIRONMENTS:
            header += f' {e:>15}'
        print(header)
        print(f'  {"-"*20}' + ''.join(f' {"-"*15}' for _ in ENVIRONMENTS))

        # Result row
        row = f'  {"Result":<20}'
        for e in ENVIRONMENTS:
            r = envs.get(e, {})
            val = r.get('result', '—')
            row += f' {val:>15}'
        print(row)

        # Run time row
        row = f'  {"Run time (s)":<20}'
        for e in ENVIRONMENTS:
            r = envs.get(e, {})
            val = r.get('time_run')
            row += f' {f"{val:.1f}" if val else "—":>15}'
        print(row)

        # Collect all perf keys
        perf_keys = set()
        for e in ENVIRONMENTS:
            r = envs.get(e, {})
            for k in r.get('perf', {}):
                perf_keys.add(k)

        for pk in sorted(perf_keys):
            row = f'  {pk:<20}'
            for e in ENVIRONMENTS:
                r = envs.get(e, {})
                pv = r.get('perf', {}).get(pk, {})
                if isinstance(pv, dict):
                    val = pv.get('value', '—')
                else:
                    val = pv
                row += f' {str(val):>15}'
            print(row)

        # Fail reason
        for e in ENVIRONMENTS:
            r = envs.get(e, {})
            fr = r.get('fail_reason')
            if fr:
                print(f'  [{e}] FAILED: {fr[:120]}')


def main():
    if len(sys.argv) < 3:
        print('Usage: compare_compilers.py <reframe_path> <tag>')
        print()
        print('Example:')
        print('  python3 scripts/compare_compilers.py application/gromacs gromacs')
        print('  python3 scripts/compare_compilers.py basics/hello smoke')
        sys.exit(1)

    path = sys.argv[1]
    tag = sys.argv[2]

    print(f'Comparing compilers for: {path} (tag={tag})')
    print(f'Environments: {", ".join(ENVIRONMENTS)}')
    print()

    all_results = {}
    for env in ENVIRONMENTS:
        data = run_benchmark(path, tag, env)
        if data:
            all_results[env] = extract_perf_values(data)

    if not all_results:
        print('No results obtained from any environment.')
        sys.exit(1)

    print_table(all_results)

    # Environment detection
    print(f'\n{"="*60}')
    print('  Environment Availability')
    print(f'{"="*60}')
    for env in ENVIRONMENTS:
        available = env in all_results and any(
            r.get('result') != 'fail' for r in all_results[env]
        )
        status = 'AVAILABLE' if available else 'FAILED/UNAVAILABLE'
        print(f'  {env:<15} {status}')


if __name__ == '__main__':
    main()
