# HPC_Test_Suite

A complete testing and benchmarking framework for HPC applications, built on **ReFrame 4.7.3+** with **Continus Bench** CI-driven benchmarking.

## Installation

### Prerequisites
- Python 3.7+
- `pip` (Python package manager)

### Install

```bash
# 1. Clone the repository
git clone <repo-url>
cd HPC_Test_Suite

# 2. Install everything (reframe + continusbench + dependencies)
pip install -r requirements.txt
pip install -e .

# 3. Verify
continusbench --help
reframe --version
```

**That's it.** No `setup.sh`, no Spack, no manual environment setup needed for the CLI.

ReFrame environment variables (`RFM_CONFIG_FILES`, `RFM_CHECK_SEARCH_PATH`, etc.) are **auto-set** by `continusbench run`. For direct `reframe` usage, see [Direct ReFrame Usage](#direct-reframe-usage).

### Quick Start

```bash
# List all discoverable tests (~135)
reframe -c . -l

# List by tag (40 tags across the suite)
reframe --list-tags -c .
reframe -c . -t smoke -l
reframe -c . -t gpu -l

# Run smoke tests
reframe -c . -t smoke -r

# Run benchmarks with env capture + HTML report
./scripts/run_benchmark.sh . cpu smoke
```

## Continus Bench CLI

The `continusbench` command provides 8 tools:

### System Onboarding

```bash
continusbench add-system
```

### Experiment Management

```bash
continusbench add-experiment
continusbench run benchmarks/specs/hpcg.yaml
continusbench run my-experiment --dry-run
```

### Validation

```bash
continusbench validate benchmarks/specs/hpcg.yaml
continusbench validate application/lammps/lammps.py
```

### Test Generation

```bash
continusbench generate-tests benchmarks/specs/hpcg.yaml -o generated/
reframe -c generated/ -r
```

### Reporting

```bash
reframe -c . -t smoke --report-file=report.json -r
continusbench report report.json -o report.html
continusbench report report.json -o report.csv --format csv
```

### Run Comparison

```bash
continusbench compare baseline.json candidate.json -o comparison.html
```

### Listing Systems

```bash
continusbench list-systems
```

## Direct ReFrame Usage

If using `reframe` directly (not through `continusbench run`), set the required environment variables:

```bash
# One-time setup (optional — for direct reframe use)
source setup.sh

# Or export manually:
export RFM_CONFIG_FILES="${PWD}/config/common/settings.py:${PWD}/config/environments/settings.py:${PWD}/config/pseudo-cluster/settings.py"
export RFM_CHECK_SEARCH_PATH="${PWD}"
export RFM_CHECK_SEARCH_RECURSIVE=yes
export RFM_GENERATE_FILE_REPORTS=true

reframe -c . -l
```

## Structure

```
hpctestlib/         # 17 system/hardware tests (HPL, STREAM, OSU, GPU burn, Horovod, etc.)
  application/        # 9 HPC application benchmarks (GROMACS, LAMMPS, NAMD, WRF, OpenFOAM, etc.)
  basics/             # 6 "hello world" sanity tests (C, C++, OpenMP, MPI)
config/             # Multi-file ReFrame configuration
  common/              # Shared settings
  environments/        # Compiler environment definitions
  pseudo-cluster/      # System-specific config
  systems/             # System definitions (add-system output)
  partitions/          # Partition overrides
  generated/           # Auto-generated ReFrame configs
continuousbench/    # Core Continus Bench framework
  cli/                 # Typer CLI (8 commands)
  generators/          # System/experiment/test YAML generators
  hooks/               # ReFrame hooks (env_capture, spack_build)
  templates/           # ReFrame template base classes
  execution/           # Benchmark executor
  collectors/          # Result collection and regression detection
  reporting/           # Multi-format report engine
  validators/          # Benchmark spec validation
  utils/               # Config management, YAML helpers
scripts/            # Utilities (env snapshot, report generation, run/compare helpers)
benchmarks/specs/   # YAML benchmark definitions (HPCG, GROMACS, hello)
```

## Usage Workflows

### Daily: Run Smoke Tests

```bash
./scripts/run_benchmark.sh . cpu smoke
```

### Nightly: Run Full Suite

```bash
reframe -c . -t nightly --report-file=nightly.json -r
continusbench report nightly.json -o nightly.html
```

### Onboarding a New HPC System

```bash
continusbench add-system
# Then configure config/pseudo-cluster/settings.py
```

### Tracking Performance Regressions

```bash
continusbench run benchmarks/specs/hpcg.yaml
# ... after software update ...
continusbench run benchmarks/specs/hpcg.yaml
continusbench compare baseline.json candidate.json -o regression.html
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

## Adding a New Benchmark

See [`continuousbench/README.md`](continuousbench/README.md#adding-a-new-benchmark) for three approaches:

1. **Standard ReFrame test** with env capture hook
2. **Template base class** (SingleNodeThroughput, StrongScaling, etc.)
3. **YAML spec + code generation**:
   ```bash
   continusbench validate benchmarks/specs/myapp.yaml
   continusbench generate-tests benchmarks/specs/myapp.yaml -o generated/
   ```

## System Portability

- Benchmarks use `valid_systems = ['*']` for cross-system portability
- Spack auto-install (`spack_ensure()`) handles missing benchmark software
- ReFrame is installed via pip — no system-level package manager needed

## CI Integration

Two GitHub Actions workflows:

- **`reframe-test.yml`** — Full test suite on push to main and PRs
- **`continuousbench-smoke.yml`** — Smoke tests on every PR

## ReFrame Tips (v4.7.3)

- Every `@rfm.simple_test` **must** have `valid_systems` and `valid_prog_environs`
- `sourcesdir = 'src'` required for compilation tests
- Use `parameter([vals])` for multi-value test variants
- Variant filter: use `-n 'ClassName.*variant=value'` (not `%`)
- `spack_ensure(spec)` in `@run_before('run')` — auto-installs apps via Spack
- `add_env_capture(self)` in `@run_before('run')` — env snapshot after run

## Documentation

| Document | Contents |
|----------|----------|
| [`continuousbench/README.md`](continuousbench/README.md) | Framework internals, adding benchmarks, CI setup |
