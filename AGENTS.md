# HPC_Test_Suite — Agent Guide

## Environment
```bash
source setup.sh          # loads spack + reframe 4.7.3
```
Sets `RFM_CONFIG_FILES` (3 colon-separated files: `common/`, `environments/`, `pseudo-cluster/`),
`RFM_CHECK_SEARCH_PATH`, `RFM_GENERATE_FILE_REPORTS=true`.

## Installation
```bash
pip install -r requirements.txt     # install Python deps
pip install -e .                    # install continusbench CLI in dev mode
continusbench --help                # verify the binary works
```

## Key Commands
```bash
reframe -c <path> -l                                                     # list tests
reframe -c <path> -S valid_systems=<sys>:<part> -S valid_prog_environs=<env> -r  # run
reframe -c . -t <tag> -l                                                 # list by tag
reframe --list-tags -c .                                                  # all 40 tags
reframe -n 'ClassName.*variant=value' ...                                 # specific param variant
./scripts/run_benchmark.sh [path] [partition] [tag]                       # runner + HTML report
continusbench --help                                                     # Continus Bench CLI
continusbench list-systems                                               # list configured systems
continusbench validate <spec.yaml>                                       # validate a benchmark spec
```

## CI
- Two self-hosted workflows: `reframe-test.yml` (push to main, PR) and `continuousbench-smoke.yml` (PR only).
- Both `source setup.sh` and use `paramrudra.snbose:cpu` + `gnu`.

## Config
- 3-file config: `config/{common,environments,pseudo-cluster}/settings.py` (order matters, via `RFM_CONFIG_FILES`).
- Single system `paramrudra.snbose` with 4 partitions: `login` (local), `cpu` (SLURM), `hm` (SLURM), `gpu` (SLURM + CUDA).
- Working env: `gnu`. Others: `foss` (buggy mpicc), `intel` (not installed), `spack-only`/`builtin` (no compiler).

## Test Structure
- **application/** (9 app benchmarks) — all tagged, all use `spack_ensure()` + `add_env_capture()`, `valid_systems = ['*']`
- **basics/** (6 hello-style tests) — tagged `{smoke, cpu, basics}`, compilation tests with `sourcesdir = 'src'`
- **hpctestlib/** (17 tests: HPCG, HPL, STREAM, OSU, GPU burn, Horovod, etc.) — all have env_capture hook

## Framework Quirks (ReFrame 4.7.3)
- Every `@rfm.simple_test` **must** have `valid_systems` and `valid_prog_environs`
- `sourcesdir = 'src'` required for compilation tests
- `feature` attribute → `self.current_partition.features` (NOT on Environment)
- Wall-time capture: last `prerun_cmds` entry must be `'time \\'`
- Swap launcher: `self.job.launcher = getlauncher('mpirun')()`
- Multi-value tests: `num_process = parameter([48, 96, 192, 384])`
- Shared imports pattern: `sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'module'))`
- Variant filter: `%` in names → use `ClassName.*variant=value` (not `ClassName %variant=value`)
- `spack_ensure(spec)` in `@run_before('run')` — auto-installs via Spack, caches results
- `add_env_capture(self)` in `@run_before('run')` — adds `env_snapshot.sh` as postrun_cmd

## Continus Bench CLI
| Command | Purpose |
|---------|---------|
| `add-system` | Interactive system onboarding → YAML |
| `add-experiment` | Interactive experiment creation |
| `run <experiment>` | Execute a benchmark experiment |
| `report <json> -o <html>` | Generate HTML report from ReFrame JSON |
| `compare <a.json> <b.json>` | Compare two runs |
| `validate <path>` | Validate YAML benchmark spec |
| `generate-tests <spec> -o <dir>` | Generate ReFrame tests from YAML |
| `list-systems` | List configured systems |

## Shared Utility
`application/module/module.py` — `parse_time_cmd()` (converts `time` output to float seconds) and `benchmark_para(n)`.
