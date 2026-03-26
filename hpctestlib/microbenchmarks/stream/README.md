# CPU STREAM Memory Bandwidth Benchmark — ReFrame Test Suite

STREAM benchmark for measuring CPU memory bandwidth on `param system`.  
Part of the `HPC_Test_Suite` microbenchmark collection.

---

## Overview

| Test | What it measures |
|---|---|
| `HardwareDetectTest` | CPU model, socket count, DIMM count, DDR frequency |
| `TheoreticalBWTest` | Theoretical peak DRAM bandwidth from hardware specs |
| `StreamMultiSysTest` | Measured memory bandwidth via STREAM kernels |

All three tests run in a dependency chain:

```
HardwareDetectTest → TheoreticalBWTest → StreamMultiSysTest
```

---

## Hardware — paramrudra.snbose

| Property | Value |
|---|---|
| CPU | Intel Xeon Gold 6240R (Cascade Lake) |
| Sockets | 2 per node |
| Cores | 24 per socket (48 total, no HT) |
| Memory | DDR4-2933 |
| Channels | 6 per socket |
| Per-socket peak | 281.6 GB/s |
| Dual-socket peak | 563.2 GB/s |

---

## Expected Results

### Single socket — 24 threads (default)

| Kernel | Formula | Theoretical | Typical Measured | Efficiency |
|---|---|---|---|---|
| Copy | a=b | 281.6 GB/s | ~198000 MB/s | ~70% |
| Scale | a=scalar×b | 281.6 GB/s | ~143000 MB/s | ~51% |
| Add | a=b+c | 281.6 GB/s | ~165000 MB/s | ~59% |
| Triad | a=b+scalar×c | 281.6 GB/s | ~172000 MB/s | ~61% |

### Dual socket — 48 threads

| Kernel | Theoretical | Typical Measured | Efficiency |
|---|---|---|---|
| Copy | 563.2 GB/s | ~300000 MB/s | ~53% |
| Triad | 563.2 GB/s | ~242000 MB/s | ~43% |

> **Note:** Dual-socket efficiency is lower than single-socket due to
> NUMA cross-socket memory access penalty (~8-12% typical reduction).

---

## Quick Start

```bash
cd /home/cdacapp01/HPC_Test_Suite

# Single socket — 24 threads on CPU partition
reframe -S valid_systems=paramrudra.snbose:cpu \
         -S valid_prog_environs=gnu \
         -c hpctestlib/microbenchmarks/stream/stream.py -r

# Single socket — 24 threads on GPU partition
reframe -S valid_systems=paramrudra.snbose:gpu \
         -S valid_prog_environs=gnu \
         -c hpctestlib/microbenchmarks/stream/stream.py -r

# Dual socket — 48 threads (measures NUMA effect)
reframe -S valid_systems=paramrudra.snbose:cpu \
         -S valid_prog_environs=gnu \
         -S "StreamMultiSysTest.cores={'paramrudra.snbose:cpu':48}" \
         -c hpctestlib/microbenchmarks/stream/stream.py -r

# Multi-node fleet check — 4 nodes, each measured independently
reframe -S valid_systems=paramrudra.snbose:cpu \
         -S valid_prog_environs=gnu \
         -S StreamMultiSysTest.num_nodes=4 \
         -c hpctestlib/microbenchmarks/stream/stream.py -r

# List all tests without running
reframe -c hpctestlib/microbenchmarks/stream/stream.py --list

# Smoke check only
reframe -S valid_systems=paramrudra.snbose:cpu \
         -S valid_prog_environs=gnu \
         --tag smoke \
         -c hpctestlib/microbenchmarks/stream/stream.py -r
```

---

## STREAM Kernels

```
Copy:  a[i] = b[i]
Scale: a[i] = scalar × b[i]
Add:   a[i] = b[i] + c[i]
Triad: a[i] = b[i] + scalar × c[i]   ← primary metric
```

**Array size:** `STREAM_ARRAY_SIZE = 2^25 = 33,554,432 elements`  
Each array = 256 MB (double precision) → total 768 MB >> LLC (35.75 MB on Gold 6240R)  
This ensures the benchmark is memory-bound, not cache-bound.

**Iterations:** `NTIMES = 20` — best time across 20 runs is reported.

---

## Performance References

References are **auto-computed** — no hardcoded MB/s values.

```
reference_MB_s = theoretical_per_socket_GB_s × efficiency_target × 1000

Example for Gold 6240R (281.6 GB/s per socket):
  Copy  ref = 281.6 × 0.60 × 1000 = 168,960 MB/s
  Scale ref = 281.6 × 0.41 × 1000 = 115,456 MB/s
  Add   ref = 281.6 × 0.49 × 1000 = 137,984 MB/s
  Triad ref = 281.6 × 0.51 × 1000 = 143,616 MB/s

Test fails if measured value drops more than 10% below reference.
```

**Efficiency targets (conservative, tuned from measurements):**

| Kernel | Target | Ref (Gold 6240R) | Measured | Margin |
|---|---|---|---|---|
| Copy | 60% | 168,960 MB/s | ~198,000 MB/s | +17% |
| Scale | 41% | 115,456 MB/s | ~143,000 MB/s | +24% |
| Add | 49% | 137,984 MB/s | ~165,000 MB/s | +20% |
| Triad | 51% | 143,616 MB/s | ~172,000 MB/s | +20% |

After establishing stable baselines, tighten targets:

```bash
-S "StreamMultiSysTest.efficiency_targets={'Copy':0.65,'Scale':0.47,'Add':0.55,'Triad':0.57}"
```

---

## Theoretical Bandwidth Detection

`TheoreticalBWTest` detects hardware specs automatically.

**Detection priority:**

```
1. dmidecode — counts populated DIMM slots per socket   (most accurate)
2. CPU model string lookup table                        (model-specific)
3. User fallback values                                 (always succeeds)
```

**CPU lookup table includes:**

| Family | Channels | Freq | Example |
|---|---|---|---|
| Cascade Lake Gold 62xx | 6 | 2933 MHz | Gold 6240R ✓ |
| Ice Lake Gold | 8 | 3200 MHz | Gold 6338 |
| Sapphire Rapids | 8 | 4800 MHz | Platinum 8480+ |
| AMD EPYC Genoa | 12 | 4800 MHz | EPYC 9654 |
| AMD EPYC Milan | 8 | 3200 MHz | EPYC 7763 |
| ARM Neoverse V2 | 8 | 4800 MHz | Grace |

If your CPU is not in the table, set fallback values:

```bash
-S TheoreticalBWTest.fallback_channels=6
-S TheoreticalBWTest.fallback_freq_mhz=2933.0
-S TheoreticalBWTest.fallback_sockets=2
```

---

## Command Line Overrides

All test variables can be set via `-S` without editing the file:

```bash
# Change thread count (affects which sockets are active)
-S "StreamMultiSysTest.cores={'paramrudra.snbose:cpu':48}"

# Change number of nodes for multi-node consistency check
-S StreamMultiSysTest.num_nodes=8

# Tighten efficiency targets after measuring stable baseline
-S "StreamMultiSysTest.efficiency_targets={'Copy':0.65,'Scale':0.47,'Add':0.55,'Triad':0.57}"

# Override hardware detection if dmidecode unavailable
-S TheoreticalBWTest.fallback_channels=6
-S TheoreticalBWTest.fallback_freq_mhz=2933.0

# Change compiler flags
-S "StreamMultiSysTest.flags={'gnu':['-fopenmp','-O3','-march=native']}"
```

---

## Scaling Behaviour

### Thread count → active sockets

| Threads | Active sockets | Channels | Theoretical |
|---|---|---|---|
| 1–24 | 1 | 6 | 281.6 GB/s |
| 25–48 | 2 | 12 | 563.2 GB/s |

The test automatically selects the efficiency target matching the number
of active sockets. Dual-socket targets are lower to account for the
NUMA penalty.

### Multi-node runs

Setting `num_nodes > 1` tests consistency across nodes.  
Each node runs STREAM independently — reference stays **per-node**.  
This catches nodes with bad DIMMs or misconfigured NUMA policy.

```
Node 1: ~172,000 MB/s  ✓
Node 2: ~171,500 MB/s  ✓
Node 3: ~172,200 MB/s  ✓
Node 4:  ~98,000 MB/s  ✗ ← bad DIMM detected
```

---

## File Structure

```
hpctestlib/microbenchmarks/stream/
└── stream.py               # All three tests in one file

    Classes:
      HardwareDetectTest    — lscpu + dmidecode + numactl
      TheoreticalBWTest     — bandwidth calculation from hw specs
      StreamMultiSysTest    — STREAM benchmark (gnu and intel envs)
```

**Source:** STREAM is downloaded at build time from:  
`https://raw.githubusercontent.com/jeffhammond/STREAM/master/stream.c`

---

## Build Details

STREAM is compiled by ReFrame using the `SingleSource` build system.

**Compile flags (gnu):**
```
-fopenmp -O3 -march=native -Wall
-DSTREAM_ARRAY_SIZE=$((1 << 25))
-DNTIMES=20
```

**Compile flags (intel):**
```
-qopenmp -O3 -xHost -Wall
-DSTREAM_ARRAY_SIZE=$((1 << 25))
-DNTIMES=20
```

**Runtime environment:**
```
OMP_NUM_THREADS = 24        (1 socket — change to 48 for dual socket)
OMP_PROC_BIND   = close     (bind threads to adjacent cores)
OMP_PLACES      = cores     (one thread per physical core)
```

---

## Troubleshooting

### `Solution Validates` not found
STREAM failed its internal correctness check. Usually caused by:
- Memory error on the node (run `memtest` to verify)
- Compiler optimisation stripping the validation loop (remove `-O3`)

### `TheoreticalBWTest` shows `fallback:no_cpu_match`
CPU model not in the lookup table. Add it to `_detect_from_cpu_model`
or set fallback values via `-S`:
```bash
-S TheoreticalBWTest.fallback_channels=8
-S TheoreticalBWTest.fallback_freq_mhz=3200.0
```

### Results much lower than expected
Check NUMA binding is active:
```bash
srun --partition=cpu --nodes=1 --ntasks=1 --cpus-per-task=24 \
    numactl --hardware
```
Ensure `OMP_PROC_BIND=close` and `OMP_PLACES=cores` are set.

### wget fails during build (no internet on compute node)
STREAM source is downloaded during the compile phase which runs on the
compute node. If compute nodes have no internet, pre-download on login:
```bash
wget -q https://raw.githubusercontent.com/jeffhammond/STREAM/master/stream.c \
    -O hpctestlib/microbenchmarks/stream/stream.c
```
Then change `prebuild_cmds` in `stream.py` to copy the local file
instead of downloading:
```python
prebuild_cmds = ['cp $RFM_TEST_STAGEDIR/../../../stream.c .']
```

---

## Related Tests

| File | Tests |
|---|---|
| `hpctestlib/microbenchmarks/stream/stream.py` | CPU STREAM (this file) |
| `hpctestlib/microbenchmarks/Babelstream/babelstream.py` | GPU HBM bandwidth |
| `hpctestlib/system/fs/mnt_opts.py` | Lustre filesystem checks |

---

## Maintainer

CDAC HPC Team — `cdacapp01@paramrudra.snbose`  
ReFrame version: 4.7.3  
Last updated: March 2026
