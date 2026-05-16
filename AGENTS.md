# HPC_Test_Suite — Agent Guide

## Environment Setup
```bash
source setup.sh          # loads spack + reframe 4.7.3, sets RFM_CONFIG_FILES & RFM_CHECK_SEARCH_PATH
```
ReFrame is loaded via spack, not pip. Auto-completion sourced from spack install prefix.

## Key Commands
- `reframe -c <path> -l` — list tests (zero-warnings gate)
- `reframe -c <path> -S valid_systems=<sys>:<part> -S valid_prog_environs=<env> -r` — run
- `reframe -n 'ClassName.*variant=value'` — regex filter for specific variants
- `reframe -c application/ -l` — 62 tests; `basics/ -l` → 7; `hpctestlib/ -l` → 67
- `reframe -c . -t <tag> -l` — list by tag; `reframe --list-tags -c .` — all 40 tags
- `./scripts/run_benchmark.sh [path] [partition] [tag]` — convenience runner
- `python3 scripts/compare_compilers.py <path> <tag>` — cross-compiler perf comparison

## Architecture
- **3 tiers**: `application/` (9 app benchmarks, all tagged), `basics/` (6 "hello" prints), `hpctestlib/` (17 tests across 7 categories)
- **Single system**: `paramrudra.snbose` with 4 partitions: `login` (local), `cpu`, `hm`, `gpu` (SLURM)
- **Environments**: `gnu` (works), `foss` (buggy mpicc), `intel` (not installed), `spack-only` (no compiler), `builtin` (no compiler)
- **Config**: 3-file split: `config/{common,environments,pseudo-cluster}/settings.py`
- **Shared utility**: `application/module/module.py` — `parse_time_cmd()` and `benchmark_para()`

## Framework Quirks (ReFrame 4.7.3)
- Every `@rfm.simple_test` class **must** have `valid_systems` and `valid_prog_environs`
- `sourcesdir = 'src'` required for compilation tests
- Use `getlauncher('mpirun')()` or `getlauncher('srun')()` to swap launchers
- `parameter([vals])` for multi-value test variants
- `feature` attribute on `Partition`, not `Environment` — use `self.current_partition.features`
- Wall-time capture: last `prerun_cmds` entry = `'time \\'`
- Shared imports: `sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'module'))`
- `/home/samirs/` paths remain in `application/Castro/castro.py` (now via env vars)

## Running Specific Variants
To run a specific parameterized variant, use regex in `-n` to match the variant part:
```bash
# List all variants first
reframe -c <path> -l

# Run a specific variant using ClassName.*variant=value pattern
reframe -c <path> -n 'ClassName.*variant=value' -S valid_systems=<sys>:<part> -S valid_prog_environs=<env> -r
```
**Important**: The `%` in variant names is NOT a regex metacharacter, but ReFrame's `-n` filter requires regex `.*` between the class name and variant info. Do NOT use `-n 'ClassName %variant=value'` (space+percent) — it won't match.

## ContinuousBench Framework

### Structure
- `scripts/env_snapshot.sh` — environment provenance capture (JSON sidecar on compute nodes)
- `scripts/generate_report.py` — ReFrame JSON report → HTML report with env sidecars
- `scripts/run_benchmark.sh` — convenience runner
- `scripts/compare_compilers.py` — cross-compiler performance comparison tool
- `continuousbench/hooks/env_capture.py` — `add_env_capture(test)` utility
- `continuousbench/hooks/spack_build.py` — `spack_ensure(spec)` auto-install via Spack
- `continuousbench/templates/_base.py` — template base classes
- `benchmarks/specs/` — YAML benchmark specs

### Tag System
- 40 tags across suite: `smoke`, `cpu`, `gpu`, `basics`, `sciapp`, `microbenchmark`, `ml`, `chem`, `cfd`, `weather`, `amrex`, `pilot`, etc.
- **Application** (9 files): all tagged with domain + hardware tags
- **hpctestlib** (12 files): all tagged, all have env_capture hook
- **Basics** (6 tests): tagged `{smoke, cpu, basics}` + sub-tags

### Spack Auto-Install (Portability)
All application benchmarks use `spack_ensure(spec)` in their `@run_before('run')` hook:
- Checks `spack location -i <spec>` 
- If not found, runs `spack install --no-checksum <spec>`
- Falls back to PATH/modules if Spack unavailable
- Benchmarks use `valid_systems = ['*']` for cross-system portability

### Env Capture Flow
1. `@run_before('run')` → `add_env_capture(self)` → adds `env_snapshot.sh` as postrun_cmd
2. Compute node captures: modules, nvidia-smi, ldd, SLURM vars, kernel, CPU → JSON
3. Sidecar preserved via `keep_files`, lands in `outputdir`
4. `generate_report.py` reads report + sidecars → HTML

### Adding a New Benchmark
```python
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure

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
```

## Current State
- **~135 tests discoverable, zero warnings** (application=62 + basics=7 + hpctestlib=67)
- **All application benchmarks tagged** (18 tags) + **hpctestlib all have env_capture**
- **40 tags total** across the suite
- **Castro hardcoded paths replaced** with env var fallbacks
- README.md for ContinuousBench at `continuousbench/README.md`
- **Next**: CI runner provisioning, InfluxDB+Grafana, YAML spec wiring
