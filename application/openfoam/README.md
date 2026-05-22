# OpenFOAM Application Tests

OpenFOAM computational fluid dynamics benchmarks.

## Test Classes

| Class | Partition | Description |
|---|---|---|
| `openfoamTest` | cpu | simpleFoam motorbike benchmark (48-384 processes) |

## Quick Start

```bash
reframe -c application/openfoam/ -l

# Run a specific test / variant on CPU partition
reframe -c application/openfoam/ -n 'openfoamTest.*np=48' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
```

## Dependencies

- Module: `openfoam/ggn7wsm`, `intel-oneapi-mpi/3alw73q`
- Input data: `Motorbike_bench_template.tar.gz` in `/home/apps/hpc_inputs/OPENFOAM` link: https://www.cfdsupport.com/motorbike-cpu-processor-benchmark/
- Input data: `batteryCooling-12.tar.gz` in `/home/apps/hpc_inputs/OPENFOAM` link:https://holzmann-cfd.com/community/training-cases/battery-cooling
