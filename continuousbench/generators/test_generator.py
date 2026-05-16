import os

import yaml

TEST_TEMPLATE = '''import reframe as rfm
import reframe.utility.sanity as sn
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure


@rfm.simple_test
class {class_name}(rfm.RunOnlyRegressionTest):
    valid_systems = {valid_systems}
    valid_prog_environs = {valid_environs}
    tags = {tags}
    time_limit = '{time_limit}'
{extra_attrs}
    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @run_before('run')
    def ensure_spack(self):
        prefix = spack_ensure('{spack_spec}')
        if prefix:
            self.executable = os.path.join(prefix, 'bin', '{binary_name}')

    @sanity_function
    def validate(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('{perf_unit}')
    def extract_time(self):
        return sn.extractsingle(r'{perf_regex}', self.stdout, 1, float)
'''


class TestGenerator:
    def __init__(self):
        pass

    def generate_from_spec(self, spec_path, output_dir):
        with open(spec_path) as f:
            spec = yaml.safe_load(f)

        os.makedirs(output_dir, exist_ok=True)
        files = []

        for bench in spec.get("benchmarks", [spec]):
            class_name = bench.get("class_name", bench.get("name", "Benchmark").title().replace("-", "").replace("_", " "))
            if not class_name.endswith("Bench"):
                class_name += "Bench"

            valid_systems = bench.get("systems", ["*"])
            valid_environs = bench.get("environments", ["gnu"])
            tags = bench.get("tags", ["smoke"])
            time_limit = bench.get("time_limit", "10m")
            spack_spec = bench.get("spack_spec", "")
            binary_name = bench.get("binary", "bench")
            perf_unit = bench.get("perf_unit", "s")
            perf_regex = bench.get("perf_regex", r"Time:\s+(\S+)")

            params = bench.get("params", {})
            extra_lines = []
            extra_attrs = ""
            if params:
                for pname, pvals in params.items():
                    extra_lines.append(f"    {pname} = parameter({pvals})")
                extra_attrs = "\n" + "\n".join(extra_lines)

            if "num_tasks" in bench:
                extra_attrs += f"\n    num_tasks = {bench['num_tasks']}"
            if "num_tasks_per_node" in bench:
                extra_attrs += f"\n    num_tasks_per_node = {bench['num_tasks_per_node']}"
            if "num_gpus_per_node" in bench:
                extra_attrs += f"\n    num_gpus_per_node = {bench['num_gpus_per_node']}"

            code = TEST_TEMPLATE.format(
                class_name=class_name,
                valid_systems=valid_systems,
                valid_environs=valid_environs,
                tags=tags,
                time_limit=time_limit,
                extra_attrs=extra_attrs.rstrip("\n"),
                spack_spec=spack_spec,
                binary_name=binary_name,
                perf_unit=perf_unit,
                perf_regex=perf_regex,
            )

            filename = bench.get("name", "benchmark").lower().replace(" ", "_").replace("-", "_")
            filepath = os.path.join(output_dir, f"{filename}.py")
            with open(filepath, "w") as f:
                f.write(code)
            files.append(filepath)

        return files
