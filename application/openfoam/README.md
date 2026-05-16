# OpenFOAM Application Tests

OpenFOAM computational fluid dynamics benchmarks.

## Test Classes

| Class | Partition | Description |
|---|---|---|
| `openfoamTest` | cpu | simpleFoam motorbike benchmark (96 tasks) |
| `openfoamTestNew` | cpu | sonicFoam scaling (48-3072 processes) |
| `openfoamTest_para` | cpu | simpleFoam motorbike scaling (48-384 processes) |

## Quick Start

```bash
reframe -c application/openfoam/ -l

# Run a specific test / variant on CPU partition
reframe -c application/openfoam/ -n 'openfoamTest' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
reframe -c application/openfoam/ -n 'openfoamTestNew.*np=48' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
reframe -c application/openfoam/ -n 'openfoamTest_para.*np=48' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
```

## Dependencies

- Module: `openfoam/ggn7wsm`, `intel-oneapi-mpi/3alw73q`
- Input data: `Motorbike_bench_template.tar.gz` in `src/`
