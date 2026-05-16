import json
import os
import glob


class ResultCollector:
    def __init__(self, reports_dir=None):
        self.reports_dir = reports_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', 'reports'
        )

    def collect_all(self, pattern="*.json"):
        files = sorted(glob.glob(os.path.join(self.reports_dir, pattern)))
        results = []
        for f in files:
            data = self.load_report(f)
            if data:
                results.append(data)
        return results

    def load_report(self, path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def extract_testcases(self, report_data):
        testcases = []
        for run in report_data.get("runs", []):
            for tc in run.get("testcases", []):
                testcases.append({
                    "name": tc.get("display_name") or tc.get("name"),
                    "result": tc.get("result"),
                    "system": tc.get("system"),
                    "partition": tc.get("partition"),
                    "environ": tc.get("environ"),
                    "time_run": tc.get("time_run"),
                    "time_total": tc.get("time_total"),
                    "perfvalues": tc.get("perfvalues", {}),
                    "fail_reason": tc.get("fail_reason"),
                    "outputdir": tc.get("outputdir"),
                    "tags": tc.get("tags", []),
                    "num_tasks": tc.get("num_tasks"),
                })
        return testcases

    def find_env_sidecar(self, outputdir):
        if not outputdir or not os.path.isdir(outputdir):
            return None
        for f in os.listdir(outputdir):
            if f.startswith("env_snapshot_") and f.endswith(".json"):
                with open(os.path.join(outputdir, f)) as fh:
                    return json.load(fh)
        return None

    def summary_stats(self, testcases):
        total = len(testcases)
        passed = sum(1 for t in testcases if t["result"] == "pass")
        failed = sum(1 for t in testcases if t["result"] == "fail")
        skipped = sum(1 for t in testcases if t["result"] == "skip")
        aborted = sum(1 for t in testcases if t["result"] == "abort")
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "aborted": aborted,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
        }

    def find_performance_regressions(self, baseline, candidate, threshold=0.1):
        regressions = []
        baseline_cases = self.extract_testcases(baseline)
        candidate_cases = self.extract_testcases(candidate)

        base_map = {tc["name"]: tc for tc in baseline_cases}
        for tc in candidate_cases:
            name = tc["name"]
            base = base_map.get(name)
            if not base or tc["result"] != "pass" or base["result"] != "pass":
                continue
            for perf_key, perf_val in tc.get("perfvalues", {}).items():
                base_val = base.get("perfvalues", {}).get(perf_key, {})
                if isinstance(perf_val, dict) and isinstance(base_val, dict):
                    cv = perf_val.get("value")
                    bv = base_val.get("value")
                    if cv and bv and bv != 0:
                        change = (cv - bv) / bv
                        if abs(change) > threshold:
                            regressions.append({
                                "test": name,
                                "metric": perf_key,
                                "baseline": bv,
                                "candidate": cv,
                                "change_pct": round(change * 100, 2),
                            })
        return regressions
