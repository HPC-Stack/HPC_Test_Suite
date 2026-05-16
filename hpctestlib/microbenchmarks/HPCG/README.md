# HPCG Benchmark Tests

HPCG (High Performance Conjugate Gradients) benchmark — CPU native, GPU native, and GPU container variants.

## Test Classes

| Class | Type | Partition | Description |
|---|---|---|---|
| `HPCGRunTest` | Run | cpu/hm/gpu | CPU HPCG via spack module or installed prefix |
| `HPCGGpuRunTest` | Run | gpu | NVIDIA HPCG built from source (requires NVHPC SDK) |
| `HPCGGpuContainerTest` | Run | gpu | NVIDIA HPCG via Singularity container (NGC v25.09) |

## Quick Start

```bash
# List tests
reframe -c hpctestlib/microbenchmarks/HPCG/ -l

# CPU HPCG (1 node)
reframe -c hpctestlib/microbenchmarks/HPCG/ -n 'HPCGRunTest.*num_nodes=1' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r

# GPU HPCG container
reframe -c hpctestlib/microbenchmarks/HPCG/ -n 'HPCGGpuContainerTest' -S valid_systems=paramrudra.snbose:gpu -S valid_prog_environs=spack-only -r
```

## Parameters

- `nx`, `ny`, `nz`: Problem dimensions (default: 104 each)
- `running_time`: Benchmark duration in seconds (default: 60)
- `num_nodes`: Number of compute nodes (default: 1)
