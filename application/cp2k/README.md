# CP2K Application Tests

CP2K quantum chemistry and molecular dynamics benchmark.

## Test Classes

| Class | Partition | Description |
|---|---|---|
| `cp2ktest` | cpu | CP2K performance scaling (48-384 processes) |

## Quick Start

```bash
reframe -c application/cp2k/ -l

# Run a specific variant on CPU partition
reframe -c application/cp2k/ -n 'cp2ktest.*num_process=48' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
```

## Dependencies

- Module: `cp2k` (spack)
- Launcher overrides to `mpirun`
