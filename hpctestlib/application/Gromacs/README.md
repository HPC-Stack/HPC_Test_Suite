# GROMACS Application Tests

GROMACS molecular dynamics benchmark with Spack build, energy validation, and strong scaling.

## Test Classes

| Class | Type | Scope |
|---|---|---|
| `GromacsBuildTest` | Compile (Spack) | Builds GROMACS via Spack on the login node |
| `GromacsBenchmark` | Run | 12 variants: 6 HECBioSim inputs × 2 NB implementations (cpu/gpu) |
| `GromacsStrongScalingBenchmark` | Run | 96 variants: 6 inputs × 2 NB × 4 node counts (1,2,4,8) |

## Input Data

Six inputs from the [HECBioSim benchmark suite](https://github.com/victorusu/GROMACS_Benchmark_Suite) packaged with GROMACS 2024.2. Each is a pre-compiled `.tpr` (topology+parameter+run input) file that fixes the problem size — ideal for strong scaling where atom count stays constant as node count grows.

| Benchmark | Atoms | File Size | Purpose |
|---|---|---|---|
| Crambin | 639 | 673 KB | Smallest — quick smoke test |
| Glutamine-Binding-Protein | 22,815 | 2.5 MB | Small soluble protein |
| hEGFRDimer | 76,870 | 15 MB | Medium transmembrane dimer |
| hEGFRDimerSmallerPL | 83,268 | 15 MB | Dimer with truncated peptide ligands |
| hEGFRDimerPair | 155,654 | 37 MB | Two dimers — moderate strong-scaling workload |
| hEGFRtetramerPair | 316,464 | 73 MB | Largest — designed for multi-node scaling |

Files are downloaded once from GitHub on the login node (compute nodes have no internet) and cached in the stage directory. The same `.tpr` is reused across all node counts so the problem size is genuinely fixed.

Energy reference values (±0.1% tolerance) are validated against published GROMACS 2024.2 output to catch regressions.

## Quick Start

```bash
# List tests
reframe -c hpctestlib/application/Gromacs/ -S valid_systems=paramrudra.snbose:hm -S valid_prog_environs=gnu -l

# Run CPU benchmark
reframe -c hpctestlib/application/Gromacs/ -n 'GromacsBenchmark.*nb_impl=cpu' -S num_tasks=16 -S valid_systems=paramrudra.snbose:hm -S valid_prog_environs=gnu -r

# Run GPU benchmark
reframe -c hpctestlib/application/Gromacs/ -n 'GromacsBenchmark.*nb_impl=gpu' -S num_tasks=4 -S num_gpus_per_node=1 -S valid_systems=paramrudra.snbose:hm -S valid_prog_environs=gnu -r

# Override Spack spec for CPU-only systems (no CUDA):
reframe -c hpctestlib/application/Gromacs/ -S GromacsBuildTest.spack_spec='gromacs@2024.2 ^openmpi schedulers=slurm' -S valid_systems=paramrudra.snbose:hm -S valid_prog_environs=gnu -r
```

## Strong Scaling

```bash
# Run 1-node Crambin CPU
reframe -c hpctestlib/application/Gromacs/ -n 'GromacsStrongScalingBenchmark.*nb_impl=cpu.*num_nodes=1' -S num_tasks_per_node=48 -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r

# Run 4-node hEGFRtetramerPair GPU
reframe -c hpctestlib/application/Gromacs/ -n 'GromacsStrongScalingBenchmark.*hEGFRtetramerPair.*nb_impl=gpu.*num_nodes=4' -S num_tasks_per_node=48 -S num_gpus_per_node=2 -S valid_systems=paramrudra.snbose:gpu -S valid_prog_environs=gnu -r

# Run all strong-scaling tests matching the tag
reframe -c hpctestlib/application/Gromacs/ -t strongscaling -S num_tasks_per_node=48 -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
```

## Details

- **Build**: GROMACS is built via the ReFrame Spack build system (`CompileOnlyRegressionTest` with `build_system = 'Spack'`). The Spack spec is configurable via `GromacsBuildTest.spack_spec`.
- **Inputs**: 6 benchmark inputs from the [GROMACS Benchmark Suite](https://github.com/victorusu/GROMACS_Benchmark_Suite) are downloaded at runtime.
- **Validation**: Energy output is compared against reference values with a 0.1% tolerance.
- **Performance**: ns/day extracted from `md.log`.
- **Launcher**: Uses `mpirun` for parallel execution.
- **Dependencies**: Spack, CUDA (for GPU builds), MPI.
