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
reframe -c application/Gromacs/ -n GromacsBuildTest -r

# CPU benchmark
reframe -c application/Gromacs/ -n 'gromacTest_cpu.*num_process=48' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r

# GPU benchmark
reframe -c application/Gromacs/ -n 'gromacTest_gpu.*num_process=48' -S valid_systems=paramrudra.snbose:gpu -S valid_prog_environs=gnu -r
```

## Dependencies

- **CPU**: `gromacs/m6krxp7`, `openmpi/qmzsyj6` (spack modules)
- **GPU**: `gromacs/m6krxp7`, `openmpi/qmzsyj6`, CUDA-capable GPUs
- Input data: `water_GMX50_bare.tar.gz` in `src/`
