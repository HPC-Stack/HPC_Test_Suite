# Continus Bench

CI-driven benchmarking framework for production HPC centers, built on ReFrame 4.7.3+.

## Architecture

```
scripts/                    # Standalone utilities
  env_snapshot.sh           Capture environment provenance (kernel, modules, GPU, SLURM)
  generate_report.py        ReFrame report → HTML report with env sidecars
  run_benchmark.sh          Convenience runner for ad hoc campaigns

continuousbench/
  cli/                      Typer-based CLI (8 commands)
  generators/               System/experiment/test YAML generators
  hooks/
    env_capture.py          add_env_capture(test) — ReFrame hook for env capture
    spack_build.py          spack_ensure(spec) — auto-install software via Spack
  templates/
    _base.py                Base classes: SingleNodeThroughput, StrongScaling, etc.
  execution/                Benchmark executor with scheduler integration
  collectors/               Result collectors and regression detection
  reporting/                Multi-format report engine (HTML, CSV, JSON, comparisons)
  validators/               Benchmark spec validators
  utils/                    Config management, YAML utilities

benchmarks/
  specs/                    Declarative YAML benchmark specifications

.github/workflows/
  continuousbench-smoke.yml CI workflow (PR gate: smoke tests → HTML report artifact)
```

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt
pip install -e .

# 2. List all tests
reframe --list-tags -c .

# 3. Run smoke tests
continusbench run benchmarks/specs/hpcg.yaml

# 4. Generate report
reframe -c . -t smoke --report-file=report.json -r
continusbench report report.json -o report.html
```

ReFrame environment variables are auto-set by `continusbench run` and `./scripts/run_benchmark.sh`.
No `setup.sh` required.

## Adding a New Benchmark

### Option A: Standard ReFrame test with env capture

```python
import reframe as rfm
import reframe.utility.sanity as sn
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure

@rfm.simple_test
class MyBench(rfm.RunOnlyRegressionTest):
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'myapp', 'cpu'}

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @run_before('run')
    def ensure_spack(self):
        prefix = spack_ensure('myapp@1.0')
        if prefix:
            self.executable = os.path.join(prefix, 'bin', 'myapp')

    @sanity_function
    def validate(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s')
    def extract_time(self):
        return sn.extractsingle(r'Time:\s+(\S+)', self.stdout, 1, float)
```

### Option B: Use template base class

```python
from continuousbench.templates._base import SingleNodeThroughput

@rfm.simple_test
class MyBench(SingleNodeThroughput):
    tags = {'microbenchmark', 'custom'}
    executable = 'mybench'
```

### Option C: YAML spec + generated test

Create `benchmarks/specs/myapp.yaml`:
```yaml
name: myapp
tags: [sciapp, cpu]
systems: ['*']
environ: gnu
params:
  nodes: [1, 2, 4]
```

Generate the test:
```bash
continusbench generate-tests benchmarks/specs/myapp.yaml -o generated/
reframe -c generated/ -l
reframe -c generated/ -r
```

## Tag System

| Tag | Scope | Typical Cadence |
|-----|-------|-----------------|
| `smoke` | Sanity check (single node, < 1 min) | Every PR |
| `cpu` | CPU compute benchmarks | Daily |
| `gpu` | GPU compute benchmarks | Daily |
| `microbenchmark` | Low-level subsystem tests | Daily |
| `sciapp` | Full application kernels | Weekly |
| `nightly` | Nightly regression suite | Daily |
| `scaling` | Multi-node scaling tests | Weekly |

Run with: `reframe -c . -t <tag> -r`

## Spack Auto-Install

Benchmarks can automatically install missing software via Spack:

```python
from spack_build import spack_ensure

# In @run_before('run') hook:
prefix = spack_ensure('gromacs@2024.2')
if prefix:
    self.executable = os.path.join(prefix, 'bin', 'gmx_mpi')
```

This is **optional** — works only if Spack is available on the system.

## CI Workflow

```yaml
.github/workflows/continuousbench-smoke.yml
```

Requires:
- Self-hosted runner with Python 3.8+
- GitHub secrets: `CI_SSH_KEY`, `CI_SSH_HOST`, `CI_SSH_USER`

Triggers:
- **PR to main**: smoke tests (`-t smoke`, < 15 min)
- **Cron nightly**: full nightly suite (`-t nightly`)
- **Manual dispatch**: any tag subset

## Reporting

```bash
reframe -c . --report-file=report.json -r
continusbench report report.json -o report.html
```

The HTML report contains:
- Summary stats (passed/failed/skipped)
- Per-test timing breakdowns
- Performance values
- Environment snapshot per test (modules, GPU, SLURM, CPU, kernel)

## Cross-Compiler Analysis

```bash
for env in gnu foss intel; do
    reframe -c application/gromacs -t gromacs \
        -S valid_systems=* -S valid_prog_environs=$env \
        --report-file=report_$env.json -r
done
continusbench report report_gnu.json -o comparison_gnu.html
```
