# Castro Application Tests

Castro (AMReX-based) astrophysics simulation benchmark.

## Test Classes

| Class | Partition | Description |
|---|---|---|
| `castroTest` | cpu | OpenMP threading scaling (1-46 threads, single task) |
| `castro_mpi_Test` | cpu | MPI parallel (46 processes) |
| `castro_intelTest` | cpu | Intel compiler variant, OpenMP scaling |
| `castro_intel_mpiTest` | hm | Intel compiler + MPI parallel |

## Quick Start

```bash
reframe -c application/Castro/ -l

# Run a specific variant on CPU partition
reframe -c application/Castro/ -n 'castroTest.*num_threads=16' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
```

## Prerequisites

Requires Castro and AMReX source tree at configured paths via `AMREX_HOME`, `CASTRO_HOME`, `MICROPHYSICS_HOME` env vars.
