# GROMACS Application Tests

GROMACS molecular dynamics benchmark on Param Rudra cluster.

## Test Classes

| Class | Type | Partition | Description |
|---|---|---|---|
| `GromacsBuildTest` | Build | cpu | Build GROMACS from source via Spack |
| `gromacTest_cpu` | Run | cpu | CPU benchmark (water, 5000 steps) |
| `gromacTest_gpu` | Run | gpu | GPU benchmark (water, 50000 steps, -nb gpu) |

## Quick Start

```bash
# List tests
reframe -c application/Gromacs/ -l

# Build GROMACS
reframe -c application/Gromacs/ -n GromacsBenchmark -r

# CPU benchmark
reframe -c application/Gromacs/ -n GromacsBenchmark -S num_process=48 -S benchmark_type=cpu -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
# GPU benchmark
reframe -c application/Gromacs/ -n GromacsBenchmark -S num_process=8 -S benchmark_type=gpu -S valid_systems=paramrudra.snbose:gpu -S valid_prog_environs=gnu -r

# Replace module 
reframe -n GromacsBenchmark -M 'gromacs:gromacs/2020.5' -r
```

## Dependencies

- **CPU**: `gromacs/m6krxp7`, `openmpi/qmzsyj6` (spack modules)
- **GPU**: `gromacs/m6krxp7`, `openmpi/qmzsyj6`, CUDA-capable GPUs
- Input data: `water_GMX50_bare.tar.gz` in `src/`
