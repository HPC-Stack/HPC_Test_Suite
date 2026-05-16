# WRF Application Tests

WRF (Weather Research and Forecasting) weather simulation benchmark.

## Test Classes

| Class | Partition | Description |
|---|---|---|
| `wrfTest` | cpu | WRF scaling (48-384 processes) |

## Quick Start

```bash
reframe -c application/wrf/ -l

# Run a specific variant on CPU partition
reframe -c application/wrf/ -n 'wrfTest.*num_process=48' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
```

## Dependencies

- Module: `wrf` (spack)
- Launcher overrides to `mpirun`
