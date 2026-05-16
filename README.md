# HPC_Test_Suite

A complete testing and benchmarking framework for HPC applications, built on **ReFrame 4.7.3** with **Continus Bench** CI-driven benchmarking.

## Quick Start

```bash
# Setup environment
source setup.sh

# List all tests
reframe -c . -l

# List by tag (40 tags across suite)
reframe --list-tags -c .
reframe -c . -t smoke -l
reframe -c . -t gpu -l
reframe -c . -t sciapp -l

# Run smoke tests
reframe -c . -t smoke -r

# Run a specific test variant (use regex in -n to match variant parameters)
reframe -c application/wrf/ -n 'wrfTest.*num_process=48' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r

# Run with env capture + report
./scripts/run_benchmark.sh . cpu smoke

# Continus Bench CLI
python3 -m continuousbench.cli.main --help
python3 -m continuousbench.cli.main list-systems
python3 -m continuousbench.cli.main add-system
```

## Structure

```
application/        # 9 HPC application benchmarks (GROMACS, LAMMPS, NAMD, WRF, OpenFOAM, etc.)
basics/             # 6 "hello world" sanity tests (C, C++, OpenMP, MPI)
hpctestlib/         # 17 system/hardware tests (HPL, STREAM, OSU, GPU burn, Horovod, etc.)
config/             # Multi-file ReFrame configuration (common, environments, pseudo-cluster, systems)
continuousbench/    # Core framework (CLI, generators, hooks, templates, execution, collectors, reporting, validators)
  ├── cli/          # Typer CLI: add-system, add-experiment, run, report, compare, validate, generate-tests
  ├── generators/   # System/experiment/test YAML generators
  ├── execution/    # Benchmark executor
  ├── collectors/   # Result collection and regression detection
  ├── reporting/    # Multi-format report engine (HTML, CSV, JSON, comparisons)
  └── validators/   # Benchmark spec validation
scripts/            # Utilities (env snapshot, report generation, run/compare helpers)
benchmarks/specs/   # YAML benchmark definitions (HPCG, GROMACS specs)
```

## Continus Bench

Full documentation: [`AGENTS.md`](AGENTS.md)

Key features:
- **Environment provenance**: Every benchmark run captures kernel, modules, GPU, SLURM vars → JSON sidecar
- **HTML reports**: ReFrame JSON report → detailed HTML with env snapshots per test
- **Spack auto-install**: Missing software auto-installed via Spack (`spack_ensure()`)
- **Tag-based filtering**: 40 tags for benchmark subset selection (smoke, nightly, gpu, sciapp, etc.)
- **Cross-compiler comparison**: Compare gnu vs foss vs intel performance
- **CLI-driven onboarding**: Interactive system and experiment creation
- **Performance regression detection**: Compare runs and detect regressions
- **Multi-format reporting**: HTML, CSV, JSON summary, run comparisons

## Adding a New Benchmark

See [`continuousbench/README.md`](continuousbench/README.md#adding-a-new-benchmark) for three approaches:
1. Standard ReFrame test with env capture hook
2. Template base class
3. YAML spec + ReFrame class generation (`continus-bench generate-tests`)

## System Portability

Benchmarks use `valid_systems = ['*']` for cross-system portability.
Deploying on a new cluster requires updating only `config/pseudo-cluster/settings.py`.
Spack auto-install (`spack_ensure()`) handles missing software.
