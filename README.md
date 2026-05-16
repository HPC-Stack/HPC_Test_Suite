# HPC_Test_Suite

A complete testing and benchmarking framework for HPC applications, built on **ReFrame 4.7.3** with **Continus Bench** CI-driven benchmarking.

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd HPC_Test_Suite

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Continus Bench CLI
pip install -e .

# 4. Verify installation
continusbench --help
```

### Dependencies

| Package | Required | Purpose |
|---------|----------|---------|
| `typer` | Yes | CLI framework |
| `questionary` | Yes | Interactive prompts |
| `pyyaml` | Yes | YAML spec parsing |
| `reframe>=4.7.3` | No (benchmarks) | HPC benchmark framework |
| `jinja2` | No (reporting) | Template-based reports |
| `matplotlib` / `plotly` | No (reporting) | Chart generation |

### Quick Start

```bash
# Setup HPC environment (loads spack + reframe)
source setup.sh

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

The `continusbench` command provides 8 tools for managing benchmarks:

### System Onboarding

```bash
# Interactive — adds system to config/systems/
continusbench add-system
```
Prompts for system name, hostname, partitions, schedulers, and generates a YAML config.

### Experiment Management

```bash
# Interactive — create a benchmark experiment
continusbench add-experiment

# Run an experiment
continusbench run benchmarks/specs/hpcg.yaml

# Dry-run to preview the reframe command
continusbench run my-experiment --dry-run

# Override system/environment at runtime
continusbench run my-experiment --system mycluster:cpu --environ intel
```

### Validation

```bash
# Validate a YAML benchmark spec
continusbench validate benchmarks/specs/hpcg.yaml

# Validate a Python test file (syntax check)
continusbench validate application/lammps/lammps.py
```

### Test Generation

```bash
# Generate ReFrame test files from a YAML spec
continusbench generate-tests benchmarks/specs/hpcg.yaml -o generated/

# Run the generated tests
reframe -c generated/ -l
reframe -c generated/ -r
```

### Reporting

```bash
# Run benchmarks and save the JSON report
reframe -c . -t smoke --report-file=report.json -r

# Generate HTML report
continusbench report report.json -o report.html

# Export as CSV or JSON summary
continusbench report report.json -o report.csv --format csv
continusbench report report.json -o summary.json --format json
```

### Run Comparison

```bash
# Compare two benchmark runs (detects regressions)
continusbench compare baseline.json candidate.json -o comparison.html
```

### Listing Systems

```bash
# List all configured HPC systems
continusbench list-systems
```

## Structure

```
application/        # 9 HPC application benchmarks (GROMACS, LAMMPS, NAMD, WRF, OpenFOAM, etc.)
basics/             # 6 "hello world" sanity tests (C, C++, OpenMP, MPI)
hpctestlib/         # 17 system/hardware tests (HPL, STREAM, OSU, GPU burn, Horovod, etc.)
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
source setup.sh
./scripts/run_benchmark.sh . cpu smoke
```

### Nightly: Run Full Suite

```bash
source setup.sh
reframe -c . -t nightly --report-file=nightly.json -r
continusbench report nightly.json -o nightly.html
```

### Onboarding a New HPC System

```bash
continusbench add-system              # interactive YAML generation
# Then configure config/pseudo-cluster/settings.py
source setup.sh
reframe -c . -t smoke -r              # verify benchmarks work
```

### Creating and Running an Experiment

```bash
continusbench add-experiment           # interactive creation
continusbench run <experiment-name>    # execute
continusbench report report.json -o experiment.html  # view results
```

### Tracking Performance Regressions

```bash
# Baseline run (e.g., after install)
continusbench run benchmarks/specs/hpcg.yaml --dry-run
# ... actual run ...
continusbench report baseline.json -o baseline.html

# Candidate run (e.g., after software update)
# ... run again ...
continusbench report candidate.json -o candidate.html

# Compare
continusbench compare baseline.json candidate.json -o regression.html
```

### Generating Tests from YAML Specs

```bash
# Edit benchmarks/specs/hpcg.yaml to define parameters
continusbench generate-tests benchmarks/specs/hpcg.yaml -o generated/
reframe -c generated/ -l              # list generated tests
reframe -c generated/ -r              # run them
```

## Tag System

Tags enable benchmark subset selection:

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

## Adding a New Benchmark

Three approaches — see [`continuousbench/README.md`](continuousbench/README.md#adding-a-new-benchmark):

1. **Standard ReFrame test** with env capture hook — for full control
2. **Template base class** — for common patterns (SingleNodeThroughput, StrongScaling, etc.)
3. **YAML spec + code generation** — declarative approach:
   ```bash
   # Create benchmarks/specs/myapp.yaml
   continusbench validate benchmarks/specs/myapp.yaml
   continusbench generate-tests benchmarks/specs/myapp.yaml -o generated/
   ```

## System Portability

- Benchmarks use `valid_systems = ['*']` for cross-system portability
- Deploying on a new cluster requires updating only `config/pseudo-cluster/settings.py`
- Spack auto-install (`spack_ensure()`) handles missing software

## CI Integration

Two GitHub Actions workflows:

- **`reframe-test.yml`** — Full test suite on push to main and PRs
- **`continuousbench-smoke.yml`** — Smoke tests on every PR

## ReFrame Tips (v4.7.3)

- Every `@rfm.simple_test` **must** have `valid_systems` and `valid_prog_environs`
- `sourcesdir = 'src'` required for compilation tests
- Use `parameter([vals])` for multi-value test variants
- Variant filter: use `-n 'ClassName.*variant=value'` (not `%`)
- `spack_ensure(spec)` in `@run_before('run')` — auto-installs via Spack
- `add_env_capture(self)` in `@run_before('run')` — env snapshot after run

## Documentation

| Document | Contents |
|----------|----------|
| [`AGENTS.md`](AGENTS.md) | Complete agent reference — architecture, quirks, all commands |
| [`continuousbench/README.md`](continuousbench/README.md) | Framework internals, adding benchmarks, CI setup |
