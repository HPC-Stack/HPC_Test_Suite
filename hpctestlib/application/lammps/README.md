# LAMMPS Application Tests

LAMMPS molecular dynamics benchmark on high-memory nodes.

## Test Classes

| Class | Partition | Description |
|---|---|---|
| `lammpsTest` | hm | LAMMPS performance scaling (48-384 processes) |

## Quick Start

```bash
reframe -c application/lammps/ -l

# Run a specific variant on high-memory partition
reframe -c application/lammps/ -n 'lammpsTest.*np=48' -S valid_systems=paramrudra.snbose:hm -S valid_prog_environs=gnu -r
```

## Dependencies

- Module: `lammps/feqr35c`, `intel-oneapi-mpi/3alw73q`
- Launcher: `mpirun`
