# NAMD Application Tests

NAMD molecular dynamics benchmark.

## Test Classes

| Class | Partition | Description |
|---|---|---|
| `NamdTest` | cpu | NAMD scaling (48-384 processes, apoa1 benchmark) |

## Quick Start

```bash
reframe -c application/Namd/ -l

# Run a specific variant on CPU partition
reframe -c application/Namd/ -n 'NamdTest.*np=48' -S valid_systems=paramrudra.snbose:cpu -S valid_prog_environs=gnu -r
```

## Dependencies

- Module: `namd/ynfxnux`
- Input data: `apoa1.tar.gz` in `src/`
