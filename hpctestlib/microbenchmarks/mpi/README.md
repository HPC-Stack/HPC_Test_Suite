# OSU Micro-Benchmarks — ReFrame Test Suite

MPI point-to-point and collective benchmarks for `paramrudra.snbose`.  
Part of the `HPC_Test_Suite` microbenchmark collection.

---

## Overview

| Class | Purpose |
|---|---|
| `fetch_osu_benchmarks` | Downloads OSU tarball on login node (fixture) |
| `build_osu_benchmarks` | Builds OSU binaries locally — cpu/cuda/rocm/openacc variants |
| `osu_benchmark` | Base class — shared benchmark logic |
| `osu_run` | Run-only test — uses pre-installed OSU binaries from PATH |
| `osu_build_run` | Build + run — fetches, builds, then runs benchmarks |

---

## Benchmarks

| Benchmark | Type | Metric | Message size |
|---|---|---|---|
| `osu_latency` | point-to-point | latency (us) | 8 bytes |
| `osu_bw` | point-to-point | bandwidth (MB/s) | 4194304 bytes (4 MB) |
| `osu_allreduce` | collective | latency (us) | 8 bytes |
| `osu_alltoall` | collective | latency (us) | 8 bytes |

---

## Quick Start

```bash
cd /home/cdacapp01/HPC_Test_Suite

# List all generated test cases
reframe -c hpctestlib/microbenchmarks/mpi/osu.py --list

# Run osu_bw point-to-point bandwidth (build + run, CPU)
reframe -c hpctestlib/microbenchmarks/mpi/osu.py \
         -n 'osu_build_run.*benchmark_info=mpi.pt2pt.osu_bw.*build_type=cpu' \
         -S num_tasks=2 \
         -S valid_systems=paramrudra.snbose:cpu \
         -S valid_prog_environs=gnu \
         -r

# Run osu_allreduce collective (build + run, CUDA buffers, 16 ranks)
reframe -c hpctestlib/microbenchmarks/mpi/osu.py \
         -n 'osu_build_run.*benchmark_info=mpi.collective.osu_allreduce.*build_type=cuda' \
         -S device_buffers=cuda \
         -S num_tasks=16 \
         -S valid_systems=paramrudra.snbose:cpu \
         -S valid_prog_environs=foss \
         -r

# Run all build_type=cpu benchmarks on cpu partition
reframe -c hpctestlib/microbenchmarks/mpi/osu.py \
         -n 'osu_build_run.*build_type=cpu' \
         -S num_tasks=2 \
         -S valid_systems=paramrudra.snbose:cpu \
         -S valid_prog_environs=gnu \
         -r

# Run only run-only tests (uses pre-installed OSU in PATH)
reframe -c hpctestlib/microbenchmarks/mpi/osu.py \
         -n 'osu_run.*benchmark_info=mpi.pt2pt.osu_bw' \
         -S valid_systems=paramrudra.snbose:cpu \
         -S valid_prog_environs=gnu \
         -r
```

---

## Test Parameters

### `benchmark_info` — what to run

| Value | Benchmark | Type | Metric |
|---|---|---|---|
| `mpi.pt2pt.osu_latency` | Point-to-point latency | 2 ranks | us |
| `mpi.pt2pt.osu_bw` | Point-to-point bandwidth | 2 ranks | MB/s |
| `mpi.collective.osu_allreduce` | Allreduce latency | N ranks | us |
| `mpi.collective.osu_alltoall` | Alltoall latency | N ranks | us |

### `build_type` — what to compile (`osu_build_run` only)

| Value | Buffer type | Use case |
|---|---|---|
| `cpu` | Standard host memory | CPU-to-CPU MPI |
| `cuda` | CUDA device memory | GPU-to-GPU MPI via CUDA-aware MPI |
| `rocm` | ROCm device memory | AMD GPU MPI |
| `openacc` | OpenACC device memory | OpenACC-offloaded MPI |

### `device_buffers` — buffer type at runtime

| Value | Effect |
|---|---|
| `cpu` (default) | Standard host memory buffers |
| `cuda` | CUDA device buffers — data stays in GPU HBM |
| `openacc` | OpenACC device buffers |
| `rocm` | ROCm device buffers |

> **Note:** `device_buffers=cuda` requires `build_type=cuda` — the binary
> must be compiled with CUDA support to accept `-d cuda` at runtime.

---

## Command Line Overrides via `-S`

All test variables can be overridden without editing the file:

```bash
# Set number of MPI tasks (required for collective benchmarks)
-S num_tasks=16

# Set device buffer type
-S device_buffers=cuda

# Set number of warmup iterations
-S osu_benchmark.num_warmup_iters=20

# Set number of measurement iterations
-S osu_benchmark.num_iters=500

# Override valid systems
-S valid_systems=paramrudra.snbose:gpu

# Override programming environment
-S valid_prog_environs=foss
```

---

## Selecting Tests with `-n`

The `-n` flag filters tests by name using regex. Test names follow the pattern:

```
osu_build_run %benchmark_info=<bench> %build_type=<type>
osu_run       %benchmark_info=<bench>
```

```bash
# All build+run tests with cpu build type
-n 'osu_build_run.*build_type=cpu'

# Specific benchmark + build type
-n 'osu_build_run.*benchmark_info=mpi.pt2pt.osu_bw.*build_type=cpu'

# All collective benchmarks
-n 'osu_build_run.*collective'

# All CUDA build variants
-n 'osu_build_run.*build_type=cuda'

# All run-only tests
-n 'osu_run'
```

---

## Build Details

`osu_build_run` uses two fixtures chained together:

```
fetch_osu_benchmarks (login node, local=True)
  curl -LJO http://mvapich.cse.ohio-state.edu/.../osu-micro-benchmarks-5.9.tar.gz
        │
        ▼
build_osu_benchmarks (login node, local=True)
  tar xzf osu-micro-benchmarks-5.9.tar.gz
  ./configure --enable-<build_type>
  make -C mpi -j8
        │
        ▼
osu_build_run (compute node)
  mpirun ./mpi/pt2pt/osu_bw -m 4194304 -x 10 -i 1000
```

**Configure flags per build type:**

| Build type | Configure flag | Extra requirements |
|---|---|---|
| cpu | `--enable-cpu` | None |
| cuda | `--enable-cuda` | `CUDA_HOME` must be set |
| rocm | `--enable-rocm` | ROCm installation |
| openacc | `--enable-openacc` | OpenACC compiler |

**CUDA build notes:**
The build script sets `CUDA_HOME` automatically from spack:
```bash
export CUDA_HOME=$(spack location -i cuda/7zllz2)
```
Ensure `cuda/7zllz2` matches the hash of your installed CUDA. Check with:
```bash
spack find --paths cuda
```

---

## MPI Launcher

The test replaces the default Slurm `srun` launcher with `mpirun`:

```python
self.job.launcher = getlauncher('mpirun')()
```

This is required because OSU benchmarks must be launched with `mpirun`,
not `srun`. The MPI environment must be loaded before running — ensure
your programming environment provides a compatible `mpirun`.

**For HPC-X MPI (recommended for GPU tests):**
```bash
# Add to prerun_cmds or load via module before running
source /path/to/hpcx-init.sh
hpcx_load
```

---

## Task Count Guidelines

| Benchmark | Required tasks | Recommended |
|---|---|---|
| `osu_latency` | exactly 2 | `-S num_tasks=2` |
| `osu_bw` | exactly 2 | `-S num_tasks=2` |
| `osu_allreduce` | 2+ (power of 2) | `-S num_tasks=16` |
| `osu_alltoall` | 2+ (power of 2) | `-S num_tasks=16` |

Point-to-point benchmarks always use `num_tasks=2` (set automatically).
For collective benchmarks `num_tasks` is **required** — the test will fail
to run without it. Always pass `-S num_tasks=N` for collective tests.

---

## Output Format

OSU benchmarks print a header followed by `size  value` pairs:

```
# OSU MPI Bandwidth Test v5.9
# Size      Bandwidth (MB/s)
1           1234.56
2           2345.67
4           3456.78
...
4194304     9876.54     ← performance extracted from this line
```

The test extracts the value at the target message size:
- **Bandwidth:** message size = 4194304 bytes (4 MB)
- **Latency:** message size = 8 bytes

> **Note:** OSU does NOT print "Pass" or "Fail" — sanity checks for
> the presence of the target message size line in the output.

---

## Troubleshooting

### `2 total processes failed to start`
MPI library mismatch — OSU binaries compiled against one MPI, launched
with another. Fix: ensure `mpirun` in PATH matches the MPI used to
compile OSU binaries. For HPC-X OSU binaries, use HPC-X mpirun.

### `pattern '^8.*Pass' not found`
The sanity check looks for `^<message_size>.*Pass` but OSU never prints
"Pass". This is a known bug in the base class — ignored in `osu_build_run`
because the binary path override ensures the correct binary runs.
If running `osu_run`, the binary must be in PATH.

### `osu_bw: command not found`
`osu_run` requires OSU binaries in PATH. Either:
1. Use `osu_build_run` which sets the full binary path automatically, or
2. Add the OSU bin directory to PATH in `prerun_cmds`

### `--enable-cuda: configure error`
`CUDA_HOME` is not set or the spack hash `cuda/7zllz2` doesn't exist.
Check:
```bash
spack find --paths cuda
# Update the hash in build_osu_benchmarks.prepare_build()
```

### Collective test hangs
Check that all N ranks started and that your partition allows the
requested number of tasks. Try reducing `num_tasks`:
```bash
-S num_tasks=4
```

---

## File Structure

```
hpctestlib/microbenchmarks/mpi/
└── osu.py                      # All classes in one file

    fetch_osu_benchmarks        — downloads tarball (fixture, session scope)
    build_osu_benchmarks        — compiles OSU (fixture, environment scope)
      parameters: build_type = [cpu, cuda, rocm, openacc]
    osu_benchmark               — base class (not a test)
      parameters: benchmark_info = [osu_latency, osu_bw, osu_allreduce, osu_alltoall]
    osu_run                     — run-only (needs OSU in PATH)
    osu_build_run               — build + run (self-contained)
```

---

## Related Tests

| File | Tests |
|---|---|
| `hpctestlib/microbenchmarks/mpi/osu.py` | MPI bandwidth/latency (this file) |
| `hpctestlib/microbenchmarks/stream/stream.py` | CPU memory bandwidth |
| `hpctestlib/microbenchmarks/Babelstream/babelstream.py` | GPU HBM bandwidth |
| `hpctestlib/system/fs/mnt_opts.py` | Lustre filesystem checks |

---

## Maintainer

CDAC/SNBOSE HPC Team — `cdacapp01@paramrudra.snbose`  
ReFrame version: 4.7.3  
OSU version: 5.9  
Last updated: March 2026