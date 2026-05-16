#!/usr/bin/env python3
# Generate a detailed HTML report from ReFrame JSON report + environment sidecars.

import json
import os
import sys
from datetime import datetime


def load_report(path):
    with open(path) as f:
        return json.load(f)


def find_env_sidecar(outputdir):
    for f in os.listdir(outputdir):
        if f.startswith('env_snapshot_') and f.endswith('.json'):
            with open(os.path.join(outputdir, f)) as fh:
                return json.load(fh)
    return None


def fmt_time(seconds):
    if seconds is None:
        return '—'
    if seconds < 60:
        return f'{seconds:.2f}s'
    return f'{seconds/60:.1f}m {seconds%60:.0f}s'


def result_badge(result):
    colors = {'pass': '#27ae60', 'fail': '#e74c3c',
              'skip': '#f39c12', 'abort': '#95a5a6'}
    return f'<span style="background:{colors.get(result, "#95a5a6")}; color:white; padding:2px 8px; border-radius:3px; font-weight:bold">{result.upper()}</span>'


def generate_html(report_data, output_path):
    session = report_data.get('session_info', {})
    runs = report_data.get('runs', [])

    all_cases = []
    for run in runs:
        for tc in run.get('testcases', []):
            all_cases.append(tc)

    passed = sum(1 for tc in all_cases if tc.get('result') == 'pass')
    failed = sum(1 for tc in all_cases if tc.get('result') == 'fail')
    skipped = sum(1 for tc in all_cases if tc.get('result') == 'skip')
    aborted = sum(1 for tc in all_cases if tc.get('result') == 'abort')
    total = len(all_cases)
    pass_pct = round(passed / total * 100, 1) if total else 0

    time_start = session.get('time_start', '')
    time_end = session.get('time_end', '')
    elapsed = session.get('time_elapsed', 0)

    def make_env_table(env):
        if not env:
            return '<p class="muted">No environment snapshot found</p>'
        rows = []
        for key in ['hostname', 'kernel', 'timestamp']:
            if key in env:
                rows.append(f'<tr><td>{key}</td><td>{env[key]}</td></tr>')
        if 'cpu' in env:
            for k, v in env['cpu'].items():
                rows.append(f'<tr><td>cpu.{k}</td><td>{v}</td></tr>')
        if 'memory' in env:
            rows.append(f'<tr><td>memory.total</td><td>{env["memory"].get("total", "")}</td></tr>')
        if 'slurm' in env:
            for k, v in env['slurm'].items():
                rows.append(f'<tr><td>slurm.{k}</td><td>{v}</td></tr>')
        if 'gpu' in env and env['gpu']:
            for g in env['gpu']:
                for k, v in g.items():
                    rows.append(f'<tr><td>gpu[{g.get("index","?")}].{k}</td><td>{v}</td></tr>')
        if 'modules' in env:
            rows.append(f'<tr><td>modules</td><td style="font-size:0.85em">{env["modules"]}</td></tr>')
        if 'mpi' in env:
            rows.append(f'<tr><td>mpi</td><td>{env["mpi"]}</td></tr>')
        return f'<table class="env-table">{chr(10).join(rows)}</table>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ContinuousBench Report — {session.get('hostname', 'unknown')}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f6fa; color: #2c3e50; padding: 20px; }}
.header {{ background: #2c3e50; color: white; padding: 24px 32px; border-radius: 8px; margin-bottom: 20px; }}
.header h1 {{ font-size: 1.6em; margin-bottom: 4px; }}
.header .meta {{ color: #bdc3c7; font-size: 0.9em; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.stat-card {{ background: white; padding: 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
.stat-card .num {{ font-size: 2em; font-weight: bold; }}
.stat-card .label {{ font-size: 0.8em; color: #7f8c8d; }}
.pass .num {{ color: #27ae60; }}
.fail .num {{ color: #e74c3c; }}
.test-card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 12px; overflow: hidden; }}
.test-header {{ padding: 14px 20px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
.test-header:hover {{ background: #f8f9fa; }}
.test-name {{ font-weight: 600; }}
.test-meta {{ font-size: 0.85em; color: #7f8c8d; margin-top: 2px; }}
.details {{ padding: 0 20px 14px; display: none; font-size: 0.9em; }}
.details.open {{ display: block; }}
.details table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
.details td {{ padding: 6px 10px; border-bottom: 1px solid #ecf0f1; }}
.details td:first-child {{ font-weight: 600; color: #7f8c8d; width: 180px; }}
.env-table td {{ font-size: 0.85em; }}
.env-table td:first-child {{ width: 140px; font-family: monospace; }}
.muted {{ color: #95a5a6; font-style: italic; }}
.collapse-toggle {{ color: #3498db; cursor: pointer; user-select: none; }}
.footer {{ text-align: center; padding: 20px; color: #95a5a6; font-size: 0.8em; }}
</style>
</head>
<body>
<div class="header">
  <h1>ContinuousBench Report</h1>
  <div class="meta">
    Host: {session.get('hostname', '—')} &nbsp;|&nbsp;
    Session: {session.get('uuid', '—')[:8]} &nbsp;|&nbsp;
    Started: {time_start} &nbsp;|&nbsp;
    Elapsed: {fmt_time(elapsed)}
  </div>
</div>

<div class="summary">
  <div class="stat-card">
    <div class="num">{total}</div>
    <div class="label">Total Tests</div>
  </div>
  <div class="stat-card pass">
    <div class="num">{passed}</div>
    <div class="label">Passed ({pass_pct}%)</div>
  </div>
  <div class="stat-card fail">
    <div class="num">{failed}</div>
    <div class="label">Failed</div>
  </div>
  <div class="stat-card">
    <div class="num">{skipped}</div>
    <div class="label">Skipped</div>
  </div>
  <div class="stat-card">
    <div class="num">{fmt_time(elapsed)}</div>
    <div class="label">Duration</div>
  </div>
</div>
'''

    for tc in all_cases:
        name = tc.get('display_name') or tc.get('name', '?')
        result = tc.get('result', '?')
        system = tc.get('system', '?')
        partition = tc.get('partition', '?')
        environ = tc.get('environ', '?')
        tags = ', '.join(tc.get('tags', [])) or '—'
        fail_reason = tc.get('fail_reason', '')
        fail_phase = tc.get('fail_phase', '')
        perf = tc.get('perfvalues', {})
        modules = ', '.join(tc.get('modules', [])) or '—'

        outputdir = tc.get('outputdir', '')
        env = find_env_sidecar(outputdir) if outputdir and os.path.isdir(outputdir) else None

        perf_rows = ''
        for pname, pval in perf.items():
            perf_rows += f'<tr><td>{pname}</td><td>{json.dumps(pval)}</td></tr>'

        env_html = make_env_table(env)
        fail_html = ''
        if fail_reason:
            fail_html = f'<tr><td>Fail Reason</td><td style="color:#e74c3c">{fail_reason}</td></tr>'
        if fail_phase:
            fail_html += f'<tr><td>Fail Phase</td><td>{fail_phase}</td></tr>'

        timing_rows = ''
        for tkey in ['time_compile', 'time_run', 'time_sanity', 'time_setup', 'time_performance', 'time_total']:
            tval = tc.get(tkey)
            if tval is not None:
                timing_rows += f'<tr><td>{tkey}</td><td>{fmt_time(tval)}</td></tr>'

        # Determine toggle icon
        toggle_icon = '▸' if result == 'pass' else '▾'
        details_open = ' open' if result != 'pass' else ''

        html += f'''
<div class="test-card">
  <div class="test-header" onclick="this.nextElementSibling.classList.toggle('open'); this.querySelector('.collapse-toggle').textContent = this.querySelector('.collapse-toggle').textContent === '▸' ? '▾' : '▸'">
    <div>
      <div class="test-name">{name} {result_badge(result)}</div>
      <div class="test-meta">{system}:{partition} | {environ} | tags: {tags}</div>
    </div>
    <span class="collapse-toggle">{toggle_icon}</span>
  </div>
  <div class="details{details_open}">
    <table>
      <tr><td>Executable</td><td><code>{tc.get("executable", "")} {" ".join(tc.get("executable_opts", []))}</code></td></tr>
      <tr><td>Modules</td><td>{modules}</td></tr>
      <tr><td>Num Tasks</td><td>{tc.get("num_tasks", "—")}</td></tr>
      <tr><td>Nodes</td><td>{json.dumps(tc.get("job_nodelist", []))}</td></tr>
      {fail_html}
    </table>
    <h4 style="margin-top:12px; color:#2c3e50;">Timing</h4>
    <table>{timing_rows}</table>
'''

        if perf_rows:
            html += f'''    <h4 style="margin-top:12px; color:#2c3e50;">Performance</h4>
    <table>{perf_rows}</table>
'''

        html += f'''    <h4 style="margin-top:12px; color:#2c3e50;">Environment Snapshot</h4>
    {env_html}
  </div>
</div>
'''

    html += f'''
<div class="footer">
  Generated by ContinuousBench — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>
<script>
// Ensure fail/abort details are open by default
document.querySelectorAll('.test-card').forEach(card => {{
    const result = card.querySelector('.test-header').innerHTML;
    if (result.includes('FAIL') || result.includes('ABORT')) {{
        card.querySelector('.details').classList.add('open');
        card.querySelector('.collapse-toggle').textContent = '▾';
    }}
}});
</script>
</body>
</html>'''

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)
    print(f'Report written to {output_path}')
    return output_path


def main():
    if len(sys.argv) < 2:
        print('Usage: generate_report.py <reframe_report.json> [output.html]')
        sys.exit(1)

    report_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'continuousbench_report.html'

    report_data = load_report(report_path)
    generate_html(report_data, output_path)


if __name__ == '__main__':
    main()
