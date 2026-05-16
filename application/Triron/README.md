# Triton Application Tests

Triton multiphysics simulation benchmark (ORNL).

## Test Classes

| Class | Type | Partition | Description |
|---|---|---|---|
| `build_triton` | Build+Run | login | Build Triton from source (omp/gpu variants) |

## Quick Start

```bash
reframe -c application/Triron/ -l

# Run a specific build variant on login partition
reframe -c application/Triron/ -n 'build_triton.*build_type=hpc_omp' -S valid_systems=paramrudra.snbose:login -S valid_prog_environs=gnu -r

# Run GPU build variant
reframe -c application/Triron/ -n 'build_triton.*build_type=hpc_gpu' -S valid_systems=paramrudra.snbose:login -S valid_prog_environs=gnu -r
```

## Dependencies

- Requires internet access (git clone from code.ornl.gov)
- `gcc@13/3wdooxp`, `nvhpc/kykmjze` (spack modules)
- NVHPC SDK with HPC-X MPI for compilation
