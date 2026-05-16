# ContinuousBench

CI-driven benchmarking framework for production HPC centers, built on ReFrame.

## Architecture

```
scripts/                    # Standalone utilities
  env_snapshot.sh           Capture environment provenance (kernel, modules, GPU, SLURM)
  generate_report.py        ReFrame report → HTML report with env sidecars
  run_benchmark.sh          Convenience runner for ad hoc campaigns

continuousbench/
  hooks/
    env_capture.py          add_env_capture(test) — ReFrame hook for env capture
    spack_build.py          spack_ensure(spec) — auto-install missing software via Spack
  templates/
    _base.py                Base classes: SingleNodeThroughput, StrongScaling, etc.

benchmarks/
  specs/                    Declarative YAML benchmark specifications (metadata)

.github/workflows/
  continuousbench-smoke.yml CI workflow (PR gate: smoke tests → HTML report artifact)
```

## Quick Start

```bash
# 1. Load environment
source setup.sh

# 2. Run smoke tests (basics) with env capture + report
./scripts/run_benchmark.sh . cpu smoke

# 3. List all tags
reframe --list-tags -c .

# 4. Filter by tag
reframe -c . -t gpu -l
reframe -c hpctestlib/ -t sciapp -l
```

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
    valid_systems = ['*']      # portable across clusters
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
    # Everything else inherited from SingleNodeThroughput
```

### Option C: YAML spec + ReFrame class

Create `benchmarks/specs/myapp.yaml`:
```yaml
name: myapp
tags: [sciapp, cpu]
systems: ['*']
environ: gnu
params:
  nodes: [1, 2, 4]
```

Then create the corresponding `myapp.py` test file as in Option A.

## Tag System

Tags enable benchmark subset selection. Use hierarchical naming:

| Tag | Scope | Typical Cadence |
|-----|-------|-----------------|
| `smoke` | Sanity check (single node, < 1 min) | Every PR |
| `cpu` | CPU compute benchmarks | Daily |
| `gpu` | GPU compute benchmarks | Daily |
| `microbenchmark` | Low-level subsystem tests | Daily (nightly) |
| `sciapp` | Full application kernels | Weekly |
| `nightly` | Nightly regression suite | Daily |
| `scaling` | Multi-node scaling tests | Weekly |
| `build` | Compilation/install tests | PR + weekly |

Run with: `reframe -c . -t <tag> -r`

## Spack Auto-Install

Benchmarks automatically install missing software via Spack:

```python
from spack_build import spack_ensure

# In @run_before('run') hook:
prefix = spack_ensure('gromacs@2024.2')
if prefix:
    self.executable = os.path.join(prefix, 'bin', 'gmx_mpi')
# if spack is unavailable or install fails → falls back to PATH/modules
```

This ensures the framework works on **any** system with Spack installed. No manual module loading needed.

## CI Workflow

The provided workflow runs on every PR:

```yaml
.github/workflows/continuousbench-smoke.yml
```

Requires:
- Self-hosted runner with SSH access to SLURM login node
- GitHub secrets: `CI_SSH_KEY`, `CI_SSH_HOST`, `CI_SSH_USER`

Triggers:
- **PR to main**: smoke tests (`-t smoke`, < 15 min)
- **Cron nightly**: full nightly suite (`-t nightly`)
- **Manual dispatch**: any tag subset

## Adding a New System

Deploying on a new cluster requires one file:

```
config/systems/<new_site>/settings.py
```

This maps abstract partition names → concrete SLURM partitions, module paths, and resource limits. Benchmarks use `['*']` wildcards and auto-adapt.

## Reporting

After any run:
```bash
reframe -c . --report-file=report.json -r
python3 scripts/generate_report.py report.json report.html
```

The HTML report contains:
- Summary stats (passed/failed/skipped)
- Per-test timing breakdowns
- Performance values
- Environment snapshot per test (modules, GPU, SLURM, CPU, kernel)

## Cross-Compiler Analysis

Run the same benchmark across multiple environments to compare:

```bash
for env in gnu foss intel; do
    reframe -c application/gromacs -t gromacs \
        -S valid_systems=* -S valid_prog_environs=$env \
        --report-file=report_$env.json -r
done
python3 scripts/generate_report.py report_gnu.json comparison_gnu.html
```

The performance values per environment are captured in each report for side-by-side comparison.
