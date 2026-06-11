# HPL (Linpack) Benchmark — ReFrame Test Suite

HPL benchmark for measuring CPU and GPU FP64 compute performance on `param system`.  
Part of the `HPC_Test_Suite` microbenchmark collection.

---

## Overview

| Test | What it measures |
|---|---|
| `HPLCPUTest` | FP64 peak performance via standard CPU HPL |
| `HPLGPUTest` | FP64 peak performance via GPU-accelerated HPL (NVIDIA cuBLAS) |

Both tests are independent — no dependency chain between them.

---

## Hardware — paramrudra.snbose

### CPU nodes (rbcn*)

| Property | Value |
|---|---|
| CPU | Intel Xeon Gold 6240R (Cascade Lake) |
| Sockets | 2 per node |
| Cores | 24 per socket (48 total, no HT) |
| Boost frequency | 3.0 GHz |
| SIMD | AVX-512 (16 FP64 FLOP/cycle) |
| RAM | ~192 GB per node |
| Theoretical FP64 peak (2 sockets) | 48 × 3.0 × 16 × 2 = **6144 GFlops** |
| Expected HPL (~75% efficiency) | ~4608 GFlops |

### GPU nodes (rbgpu*)

| Property | Value |
|---|---|
| GPU | NVIDIA A100 80GB PCIe |
| GPUs per node | 2 |
| FP64 theoretical peak per GPU | 312 TFlops (312,000 GFlops) |
| Expected HPL (~70% efficiency) | ~218 TFlops per GPU |

---

## Quick Start

```bash
cd /home/cdacapp01/HPC_Test_Suite

# List both tests
reframe -c hpctestlib/microbenchmarks/HPL/hpl.py --list

# CPU — 48 MPI ranks (both sockets, auto-computes N and P×Q)
reframe -c hpctestlib/microbenchmarks/HPL/hpl.py -n HPLCPUTest \
         -S valid_systems=paramrudra.snbose:cpu \
         -S HPLCPUTest.num_tasks=48 -r

# CPU — 24 MPI ranks (single socket)
reframe -c hpctestlib/microbenchmarks/HPL/hpl.py -n HPLCPUTest \
         -S valid_systems=paramrudra.snbose:cpu \
         -S HPLCPUTest.num_tasks=24 -r

# GPU — 1 node, 2 GPUs (1 rank per node, rank owns both GPUs)
reframe -c hpctestlib/microbenchmarks/HPL/hpl.py -n HPLGPUTest \
         -S valid_systems=paramrudra.snbose:gpu \
         -S HPLGPUTest.num_tasks=1 -r

# GPU — 2 nodes, 4 GPUs total
reframe -c hpctestlib/microbenchmarks/HPL/hpl.py -n HPLGPUTest \
         -S valid_systems=paramrudra.snbose:gpu \
         -S HPLGPUTest.num_tasks=2 -r
```

---

## Architecture — Compute-Node Hardware Probe

### The problem this solves

Earlier versions called `_detect_cpu_info()` in Python during ReFrame
setup on the **login node**.  The login node has more RAM than compute
nodes (`rbcn014` has ~192 GB but the login node reported more), so N was
oversized.  At runtime, rank 23 was killed with **signal 9 (OOM kill)**
and HPL never printed `End of Tests.`, causing a sanity failure.

### The fix

`HPLCPUTest` now generates a **bash probe script** that is written to the
stage directory and executed as the first `prerun_cmd` on the **compute
node**.  The probe:

1. Reads `free -g` → actual RAM on this node
2. Reads `lscpu` → core count and max frequency
3. Reads `/proc/cpuinfo` flags → AVX-512 / AVX2 / SSE width
4. Computes `N = floor(sqrt(RAM×1e9×fraction/24) / NB) × NB`
5. Writes `HPL.dat` with the correct N
6. Prints `RFM_THEO_PEAK=<GFlops>` to stdout

ReFrame's `@sanity_function` checks that `RFM_THEO_PEAK=` appears in
stdout (proving the probe ran), and `@performance_function` extracts the
value to compute efficiency.

For `HPLGPUTest`, GPU VRAM is constant and known at setup time (A100 is
always 80 GB), so N is still computed in Python — no probe needed.

---

## HPL.dat Parameters

### N — problem size

```
N = floor(sqrt(RAM_GB × 1e9 × mem_fraction / 24) / NB) × NB

Example (192 GB RAM, 75% fill, NB=256):
  N = floor(sqrt(192e9 × 0.75 / 24) / 256) × 256
  N = floor(77,460 / 256) × 256 = 77,312
```

`mem_fraction` defaults to **0.75** for CPU (conservative, avoids OOM).
For GPU, 0.80 is safe because GPU VRAM is dedicated.

### NB — block size

| Variant | Default NB | Notes |
|---|---|---|
| CPU | 256 | Tuned for Cascade Lake LLC line size |
| GPU | 1024 | Optimal for A100 cuBLAS tile size |

### P × Q — MPI process grid

Auto-computed as the most-square factorisation of `num_tasks` with P ≤ Q:

| num_tasks | P | Q |
|---|---|---|
| 48 | 6 | 8 |
| 24 | 4 | 6 |
| 4 | 2 | 2 |
| 2 | 1 | 2 |
| 1 | 1 | 1 |

---

## Performance References

References are **auto-computed** — no hardcoded GFlops values.

```
reference_GFlops = theoretical_peak × efficiency_target

CPU example (detected on compute node rbcn014):
  probe output: RFM_THEO_PEAK=6144.0
  reference (75%) = 6144.0 × 0.75 = 4608 GFlops

GPU example (A100 × 2, 1 node):
  peak = 312000 × 2 = 624000 GFlops
  reference (70%) = 624000 × 0.70 = 436800 GFlops
```

**Test fails if measured GFlops drops more than 10% below the reference.**

Default efficiency targets:

| Variant | Target | Rationale |
|---|---|---|
| CPU | 75% | Typical HPL on Cascade Lake with AVX-512 |
| GPU | 70% | Conservative for A100 PCIe; tighten after baseline |

Tighten after establishing a stable baseline:

```bash
-S HPLCPUTest.efficiency_target=0.80
-S HPLGPUTest.efficiency_target=0.75
```

---

## Command Line Overrides

All test variables are settable via `-S`:

```bash
# Override N directly (bypasses probe auto-detection)
-S HPLCPUTest.n_size=77312

# Override NB
-S HPLCPUTest.nb_size=192

# Override P×Q grid
-S HPLCPUTest.p_grid=6 -S HPLCPUTest.q_grid=8

# Change memory fraction (lower if nodes are memory-constrained)
-S HPLCPUTest.mem_fraction=0.70

# Change efficiency target
-S HPLCPUTest.efficiency_target=0.80

# Override probe fallback values (used if lscpu/free are unavailable)
-S HPLCPUTest.fallback_ram_gb=128
-S HPLCPUTest.fallback_cores=48
-S HPLCPUTest.fallback_freq_mhz=2400
-S HPLCPUTest.fallback_flop=8

# Change HPL module
-S HPLCPUTest.hpl_module=hpl/newbuild

# GPU: different GPU type
-S HPLGPUTest.gpu_vram_gb=40.0
-S HPLGPUTest.gpu_peak_gflops=19500.0   # V100 32GB
```

---

## Module and Environment Notes

`hpl/pp7qab2` is a **gnu-toolchain build**.  `valid_prog_environs` is
set to `['gnu']` only.

> **Why `foss` is not included:** The original test included `foss` in
> `valid_prog_environs`.  Under the `foss` environment, `xhpl` was not
> on `PATH` after loading `hpl/pp7qab2`, causing every `foss` run to
> fail sanity.  Removing `foss` eliminates these false failures.

To support multiple toolchains once separate builds exist:

```python
valid_prog_environs = ['gnu', 'foss', 'intel']

hpl_modules = variable(dict, value={
    'gnu':   'hpl/pp7qab2',
    'foss':  'hpl/foss_hash',
    'intel': 'hpl/intel_hash',
}, loggable=True)

@run_before('run')
def load_module(self):
    self.modules = [self.hpl_modules.get(self.current_environ.name, 'hpl/pp7qab2')]
```

---

## GFlops Extraction

All `extractsingle` calls use the shared constant `_WR_PATTERN`:

```python
_WR_PATTERN = r'^W[A-Z0-9]+\s+\d+\s+\d+\s+\d+\s+\d+\s+\S+\s+(\S+)'
```

`\S+` matches every float format HPL produces:

| Format | Example |
|---|---|
| Plain | `4608.5` |
| Scientific | `4.608e+03` |
| Three-digit exponent | `4.608e+003` |
| Negative exponent | `1.234e-01` |
| Uppercase E | `4.608E+03` |

HPL WR line format for reference:
```
WR11C2R4   77312  256   6   8  312.45  4.608e+03
^bench      ^N    ^NB  ^P  ^Q  ^time   ^GFlops
```

---

## Scaling Behaviour

### CPU — MPI ranks and sockets

| num_tasks | Active sockets | Expected peak |
|---|---|---|
| 1–24 | 1 | ~3072 GFlops |
| 25–48 | 2 | ~6144 GFlops |

### GPU — ranks and GPUs

| num_tasks | num_tasks_per_node | Total GPUs | Expected peak |
|---|---|---|---|
| 1 | 1 | 2 | ~436,800 GFlops |
| 2 | 1 | 4 | ~873,600 GFlops |

For one MPI rank per GPU, set `num_tasks_per_node = gpus_per_node` and
set `num_tasks = total GPU count`.

---

## File Structure

```
hpctestlib/microbenchmarks/HPL/
└── hpl.py                       # Both test classes in one file

    Module-level:
      _WR_PATTERN                — shared regex for HPL WR result line
      _THEO_PEAK_TAG             — sentinel tag parsed from probe output
      _best_grid(num_tasks)      — closest-to-square P×Q factorisation
      _make_hpl_dat(...)         — HPL.dat template (GPU and N-override)
      _probe_script(...)         — bash script that runs ON compute node
                                   to detect RAM and write HPL.dat

    Classes:
      HPLCPUTest                 — compute-node probe + xhpl, gnu, cpu/hm
      HPLGPUTest                 — fixed-N from VRAM + xhpl, gnu, gpu
```

---

## Troubleshooting

### OOM kill — rank N killed with signal 9

```
mpirun noticed that process rank 23 with PID ... exited on signal 9 (Killed).
```

N is too large for the compute node's RAM.  Causes:

- `n_size` set explicitly to a value computed from login-node RAM — do not
  hardcode N from a login-node `free -g` reading
- `mem_fraction` too high for nodes with less RAM than expected
- Probe script fallback RAM value is wrong

Fix: lower `mem_fraction` or set `n_size` explicitly from the compute-node value:

```bash
# Check available RAM on a compute node first
srun --partition=cpu --nodes=1 --ntasks=1 free -g

# Then set N explicitly or lower mem_fraction
-S HPLCPUTest.mem_fraction=0.65
-S HPLCPUTest.n_size=65536
```

### `RFM_THEO_PEAK=` not found in stdout (new sanity check)

The probe script did not run or failed before printing the peak line.
Check the stage directory:

```bash
cat /scratch/cdacapp01/reframe/stage/paramrudra.snbose/cpu/gnu/HPLCPUTest/rfm_job.out | head -30
cat /scratch/cdacapp01/reframe/stage/paramrudra.snbose/cpu/gnu/HPLCPUTest/_hpl_probe.sh
```

Common cause: `python3` not on `PATH` in the compute-node job environment
(the probe uses Python to compute N).  Fix:

```bash
# Add python3 to the environment, or load a module in prerun_cmds
# Or lower to a pure-bash fallback by setting n_size explicitly:
-S HPLCPUTest.n_size=77312
```

### `End of Tests.` not found

HPL did not complete.  Check in order:

1. OOM kill (signal 9) — see above
2. `xhpl` not on `PATH` — wrong module or wrong environment
3. P×Q ≠ num_tasks — verify with `cat HPL.dat` in the stage directory
4. MPI launch failure — check `rfm_job.err` for `mpirun` errors

### CUDA dlopen warning flood on CPU nodes

```
[rbcn014:513164] 47 more processes have sent help message help-mpi-common-cuda.txt / dlopen failed
```

This is cosmetic — OpenMPI was built with CUDA support but the CPU node
has no GPU.  It is suppressed by the `--mca orte_base_help_aggregate 1`
flag added to the mpirun launcher options in this version.  If it still
appears, add to your job environment:

```bash
export OMPI_MCA_mpi_cuda_support=0
```

### `gflops` performance variable skipped

```
WARNING: skipping evaluation of performance variable 'gflops'
```

The WR line was not printed — HPL did not reach the result output stage.
Check `rfm_job.out` for the `End of Tests.` line; if absent, the job
failed before completion (usually OOM or MPI abort).

---

## Related Tests

| File | Tests |
|---|---|
| `hpctestlib/microbenchmarks/HPL/hpl.py` | CPU/GPU Linpack (this file) |
| `hpctestlib/microbenchmarks/stream/stream.py` | CPU memory bandwidth |
| `hpctestlib/microbenchmarks/Babelstream/babelstream.py` | GPU HBM bandwidth |

---

## Maintainer

CDAC HPC Team — `cdacapp01@paramrudra.snbose`  
ReFrame version: 4.9.3  
Last updated: June 2026