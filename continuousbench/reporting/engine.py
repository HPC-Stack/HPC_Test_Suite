import json
import os
import csv
from datetime import datetime

from continuousbench.collectors.result_collector import ResultCollector


class ReportingEngine:
    def __init__(self):
        self.collector = ResultCollector()

    def generate(self, report_file, output, fmt="html"):
        if fmt == "html":
            return self._generate_html(report_file, output)
        elif fmt == "csv":
            return self._generate_csv(report_file, output)
        elif fmt == "json":
            return self._generate_json_summary(report_file, output)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def _generate_html(self, report_file, output):
        report_data = self.collector.load_report(report_file)
        if not report_data:
            return None

        hostname = report_data.get("session_info", {}).get("hostname", "unknown")
        testcases = self.collector.extract_testcases(report_data)
        stats = self.collector.summary_stats(testcases)

        rows_html = ""
        for tc in testcases:
            result = tc["result"] or "?"
            badge_colors = {"pass": "#27ae60", "fail": "#e74c3c", "skip": "#f39c12", "abort": "#95a5a6"}
            color = badge_colors.get(result, "#95a5a6")
            badge = f'<span style="background:{color};color:white;padding:2px 8px;border-radius:3px;font-weight:bold">{result.upper()}</span>'
            tags = ", ".join(tc.get("tags", [])) or "—"
            perf = tc.get("perfvalues", {})
            perf_str = "; ".join(f"{k}={v.get('value','?')}" for k, v in perf.items()) if perf else "—"

            env = self.collector.find_env_sidecar(tc.get("outputdir", ""))
            env_str = ""
            if env:
                env_str = "<tr><td>Host</td><td>" + str(env.get('hostname', '?')) + "</td></tr>"
                if "cpu" in env and "model" in env["cpu"]:
                    env_str += "<tr><td>CPU</td><td>" + str(env['cpu']['model']) + "</td></tr>"
                if "gpu" in env and env["gpu"]:
                    gpu_names = ', '.join(g['name'] for g in env['gpu'])
                    env_str += "<tr><td>GPU</td><td>" + gpu_names + "</td></tr>"

            time_run = tc.get('time_run')
            time_total = tc.get('time_total')
            time_run_str = "{:.1f}s".format(time_run) if time_run else "\u2014"
            time_total_str = "{:.1f}s".format(time_total) if time_total else "\u2014"
            num_tasks = str(tc.get('num_tasks', '\u2014'))

            rows_html += """
            <div class="test-card">
                <div class="test-header" onclick="this.nextElementSibling.classList.toggle('open')">
                    <div>
                        <div class="test-name">""" + tc['name'] + " " + badge + """</div>
                        <div class="test-meta">""" + str(tc['system']) + """:""" + str(tc['partition']) + """ | """ + str(tc['environ']) + """ | tags: """ + tags + """</div>
                    </div>
                    <span class="collapse-toggle">&#9656;</span>
                </div>
                <div class="details">
                    <table>
                        <tr><td>Time (run)</td><td>""" + time_run_str + """</td></tr>
                        <tr><td>Time (total)</td><td>""" + time_total_str + """</td></tr>
                        <tr><td>Performance</td><td>""" + perf_str + """</td></tr>
                        <tr><td>Num Tasks</td><td>""" + num_tasks + """</td></tr>
                        """ + env_str + """
                    </table>
                </div>
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Continus Bench Report — {hostname}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f5f6fa; color:#2c3e50; padding:20px; }}
.header {{ background:#2c3e50; color:white; padding:24px 32px; border-radius:8px; margin-bottom:20px; }}
.header h1 {{ font-size:1.6em; }}
.header .meta {{ color:#bdc3c7; font-size:0.9em; }}
.summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:12px; margin-bottom:20px; }}
.stat-card {{ background:white; padding:16px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); text-align:center; }}
.stat-card .num {{ font-size:2em; font-weight:bold; }}
.pass .num {{ color:#27ae60; }}
.fail .num {{ color:#e74c3c; }}
.test-card {{ background:white; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); margin-bottom:12px; overflow:hidden; }}
.test-header {{ padding:14px 20px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; }}
.test-header:hover {{ background:#f8f9fa; }}
.test-name {{ font-weight:600; }}
.test-meta {{ font-size:0.85em; color:#7f8c8d; }}
.details {{ padding:0 20px 14px; display:none; font-size:0.9em; }}
.details.open {{ display:block; }}
.details table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
.details td {{ padding:6px 10px; border-bottom:1px solid #ecf0f1; }}
.details td:first-child {{ font-weight:600; color:#7f8c8d; width:160px; }}
.muted {{ color:#95a5a6; font-style:italic; }}
.footer {{ text-align:center; padding:20px; color:#95a5a6; font-size:0.8em; }}
</style>
</head>
<body>
<div class="header">
    <h1>Continus Bench Report</h1>
    <div class="meta">{hostname} &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
<div class="summary">
    <div class="stat-card"><div class="num">{stats['total']}</div><div class="label">Total</div></div>
    <div class="stat-card pass"><div class="num">{stats['passed']}</div><div class="label">Passed ({stats['pass_rate']}%)</div></div>
    <div class="stat-card fail"><div class="num">{stats['failed']}</div><div class="label">Failed</div></div>
    <div class="stat-card"><div class="num">{stats['skipped']}</div><div class="label">Skipped</div></div>
</div>
{rows_html}
<div class="footer">Generated by Continus Bench</div>
<script>
document.querySelectorAll('.test-header').forEach(h => {{
    h.addEventListener('click', function() {{
        this.nextElementSibling.classList.toggle('open');
        const t = this.querySelector('.collapse-toggle');
        t.textContent = t.textContent === '\\u25b6' ? '\\u25bc' : '\\u25b6';
    }});
}});
</script>
</body>
</html>"""

        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w") as f:
            f.write(html)
        print(f"Report written to {output}")
        return output

    def _generate_csv(self, report_file, output):
        report_data = self.collector.load_report(report_file)
        if not report_data:
            return None

        testcases = self.collector.extract_testcases(report_data)
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "result", "system", "partition", "environ", "time_run", "time_total", "fail_reason"])
            for tc in testcases:
                writer.writerow([
                    tc["name"], tc["result"], tc["system"], tc["partition"],
                    tc["environ"], tc.get("time_run"), tc.get("time_total"),
                    tc.get("fail_reason", ""),
                ])
        print(f"CSV written to {output}")
        return output

    def _generate_json_summary(self, report_file, output):
        report_data = self.collector.load_report(report_file)
        if not report_data:
            return None

        testcases = self.collector.extract_testcases(report_data)
        stats = self.collector.summary_stats(testcases)
        summary = {
            "stats": stats,
            "tests": testcases,
            "generated_at": datetime.now().isoformat(),
            "source": report_file,
        }
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"JSON summary written to {output}")
        return output

    def compare(self, run_a, run_b, output):
        data_a = self.collector.load_report(run_a)
        data_b = self.collector.load_report(run_b)
        if not data_a or not data_b:
            return None

        testcases_a = self.collector.extract_testcases(data_a)
        testcases_b = self.collector.extract_testcases(data_b)
        a_map = {tc["name"]: tc for tc in testcases_a}
        b_map = {tc["name"]: tc for tc in testcases_b}

        rows = ""
        all_names = sorted(set(list(a_map.keys()) + list(b_map.keys())))
        for name in all_names:
            ta = a_map.get(name, {})
            tb = b_map.get(name, {})
            ra = ta.get("result", "—")
            rb = tb.get("result", "—")
            tra = f"{ta.get('time_run', '—'):.1f}s" if ta.get("time_run") else "—"
            trb = f"{tb.get('time_run', '—'):.1f}s" if tb.get("time_run") else "—"

            perfa = ta.get("perfvalues", {})
            perfb = tb.get("perfvalues", {})
            perf_compare = "—"
            for k in perfa:
                if k in perfb:
                    va = perfa[k].get("value") if isinstance(perfa[k], dict) else perfa[k]
                    vb = perfb[k].get("value") if isinstance(perfb[k], dict) else perfb[k]
                    if va and vb:
                        change = ((vb - va) / va) * 100
                        color = "#e74c3c" if abs(change) > 10 else "#27ae60"
                        perf_compare = f'<span style="color:{color}">{va:.2f} &rarr; {vb:.2f} ({change:+.1f}%)</span>'

            rows += f"""
            <tr>
                <td>{name}</td>
                <td>{ra}</td>
                <td>{rb}</td>
                <td>{tra}</td>
                <td>{trb}</td>
                <td>{perf_compare}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Continus Bench Comparison</title>
<style>
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#f5f6fa; color:#2c3e50; padding:20px; }}
.header {{ background:#2c3e50; color:white; padding:24px 32px; border-radius:8px; margin-bottom:20px; }}
.header h1 {{ font-size:1.6em; }}
table {{ width:100%; border-collapse:collapse; background:white; border-radius:8px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
th {{ background:#34495e; color:white; padding:12px 16px; text-align:left; }}
td {{ padding:10px 16px; border-bottom:1px solid #ecf0f1; }}
tr:hover {{ background:#f8f9fa; }}
.footer {{ text-align:center; padding:20px; color:#95a5a6; font-size:0.8em; }}
</style>
</head>
<body>
<div class="header">
    <h1>Continus Bench Comparison</h1>
    <div class="meta">{os.path.basename(run_a)} vs {os.path.basename(run_b)}</div>
</div>
<table>
<tr>
    <th>Test</th>
    <th>Run A</th>
    <th>Run B</th>
    <th>Time A</th>
    <th>Time B</th>
    <th>Performance Change</th>
</tr>
{rows}
</table>
<div class="footer">Generated by Continus Bench &mdash; {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</body>
</html>"""

        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "w") as f:
            f.write(html)
        print(f"Comparison written to {output}")
        return output
