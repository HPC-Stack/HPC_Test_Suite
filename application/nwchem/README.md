# NWChem Application Tests

NWChem computational chemistry benchmark.

## Test Classes

| Class | Partition | Description |
|---|---|---|
| `nwchemTest` | gpu | NWChem scaling (48-384 processes) |

## Quick Start

```bash
reframe -c application/nwchem/ -l

# Run a specific variant on GPU partition
reframe -c application/nwchem/ -n 'nwchemTest.*num_process=48' -S valid_systems=paramrudra.snbose:gpu -S valid_prog_environs=gnu -r
```

## Dependencies

- Module: `nwchem` (spack), `intel-oneapi-mpi`
- GPU partition with MPI support
