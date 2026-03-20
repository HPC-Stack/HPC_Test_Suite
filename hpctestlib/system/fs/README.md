# HPC Test Suite — Filesystem Checks

Production-grade ReFrame tests for validating Lustre filesystem health on HPC clusters.
Developed and verified on **Param Rudra (paramrudra.snbose)** with AlmaLinux 8/9 CPU nodes
and Ubuntu GPU nodes (Grace Hopper).

---

## Overview

This module (`hpctestlib/system/fs/mnt_opts.py`) implements **Stage 1** of the HPC Test Suite
pipeline — filesystem validation that must pass before any benchmarks or application tests run.

```
Stage 1 — filesystem   ← this module
Stage 2 — spack
Stage 3 — microbenchmarks
Stage 4 — applications
```

### Tests included

| Test | Type | Tags | Description |
|---|---|---|---|
| `filesystem_options_check` | Gate | `system, fs, smoke, gate` | Verifies Lustre/NFS/ext4/xfs mount options from `/proc/mounts` |
| `lustre_health_check` | Gate | `system, fs, lustre, smoke, gate` | Checks OST/MDT status, free space, stripe count via `df` and `lfs` |
| `filesystem_rw_check` | Gate | `system, fs, smoke, gate` | Write/read/delete probe on `/home/$USER` and `/scratch/$USER` |
| `scratch_io_bandwidth` | Perf | `fs, perf, lustre` | Sequential write/read bandwidth via `dd` — tracks Lustre OST health over time |

### Dependency chain (pipeline gate)

```
filesystem_options_check
        │
        ▼
filesystem_rw_check
        │
        ▼
scratch_io_bandwidth
```

`lustre_health_check` runs independently in parallel.
If `filesystem_options_check` fails, `filesystem_rw_check` and
`scratch_io_bandwidth` are skipped automatically.

---

## Requirements

### Software

- **ReFrame** >= 4.7.x — install via Spack or pip
  ```bash
  pip install reframe-hpc
  # or
  spack install reframe@4.7.3
  ```
- **Python** >= 3.8
- **Slurm** (for cpu/gpu/hm partitions) or local scheduler (for login partition)
- **lfs client** — required only on GPU nodes for full Lustre checks

### Filesystem assumptions

| Mount | Type | Required options |
|---|---|---|
| `/home` | lustre | `rw,flock,lazystatfs,encrypt` |
| `/scratch` | lustre | `rw,flock,lazystatfs,encrypt` |

> **Note:** If your cluster uses different mount options, update `fs_ref_opts`
> in `filesystem_options_check`. See [Customisation](#customisation) below.

---

## Repository structure

```
HPC_Test_Suite/
├── hpctestlib/
│   └── system/
│       └── fs/
│           └── mnt_opts.py          ← this module
├── config/
│   ├── common/
│   │   └── settings.py              ← logging + general config
│   ├── environments/
│   │   └── settings.py              ← compiler environments (gnu, intel, foss ...)
│   └── pseudo-cluster/
│       └── settings.py              ← system + partition definitions
└── ci/
    └── rfm.sh                       ← convenience wrapper script
```

---

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/HPC-Stack/HPC_Test_Suite.git
cd HPC_Test_Suite
```

### 2. Set up the environment

```bash
# Add repo root to PYTHONPATH so hpc_base.py is importable
export PYTHONPATH=$(pwd):${PYTHONPATH:-}

# Load ReFrame (adjust to your module system)
module load reframe/4.7.3
# or use the spack-installed version
source /shared/spack/share/spack/setup-env.sh
spack load reframe@4.7.3
```

### 3. Configure your cluster

Edit `config/pseudo-cluster/settings.py` and update:

- `hostnames` — regex matching your login node hostname
- `resourcesdir` — path to your HPC input files
- `stagedir` / `outputdir` — preferably on local scratch, not NFS home
- `extras: lfs_available` — `True` for partitions with Lustre client tools

See [Configuration reference](#configuration-reference) for full details.

### 4. Verify the config loads correctly

```bash
# List all tests — should show 4 checks with no warnings
reframe \
  -C config/common/settings.py:config/environments/settings.py:config/pseudo-cluster/settings.py \
  -c hpctestlib/system/fs/mnt_opts.py \
  --list
```

Expected output:
```
Found 4 check(s)
  - filesystem_options_check
  - lustre_health_check
  - filesystem_rw_check
  - scratch_io_bandwidth
```

### 5. Run the filesystem tests

```bash
# Run on CPU partition with GNU environment
reframe \
  -C config/common/settings.py:config/environments/settings.py:config/pseudo-cluster/settings.py \
  -c hpctestlib/system/fs/mnt_opts.py \
  -S valid_systems=<your_system>:cpu \
  -S valid_prog_environs=gnu \
  -r

# Run on GPU partition
reframe \
  -C config/common/settings.py:config/environments/settings.py:config/pseudo-cluster/settings.py \
  -c hpctestlib/system/fs/mnt_opts.py \
  -S valid_systems=<your_system>:gpu \
  -S valid_prog_environs=gnu \
  -r
```

Replace `<your_system>` with the `name` value from your `pseudo-cluster/settings.py`
(e.g. `paramrudra.snbose`).

### 6. Using the convenience wrapper

```bash
# ci/rfm.sh handles the -C flag so you don't have to type the full path chain
./ci/rfm.sh -c hpctestlib/system/fs/mnt_opts.py \
  -S valid_systems=paramrudra.snbose:cpu \
  -S valid_prog_environs=gnu \
  -r
```

---

## Expected output — all passing

```
[==========] Running 4 check(s)

[ RUN      ] filesystem_options_check  @<system>:cpu+gnu
[ RUN      ] lustre_health_check       @<system>:cpu+gnu
[       OK ] (1/4) filesystem_options_check
[ RUN      ] filesystem_rw_check       @<system>:cpu+gnu
[       OK ] (2/4) lustre_health_check
P: scratch_free_pct: 95.0 % (r:0, l:None, u:None)
P: home_free_pct:    96.0 % (r:0, l:None, u:None)
[       OK ] (3/4) filesystem_rw_check
[ RUN      ] scratch_io_bandwidth      @<system>:cpu+gnu
[       OK ] (4/4) scratch_io_bandwidth
P: write_bw: 1.6 GB/s (r:0, l:None, u:None)
P: read_bw:  7.7 GB/s (r:0, l:None, u:None)

[  PASSED  ] Ran 4/4 test case(s) from 4 check(s) (0 failure(s))
```

---

## Configuration reference

### `config/pseudo-cluster/settings.py`

The most important settings for this module:

```python
site_configuration = {
    'systems': [
        {
            'name': 'your_cluster_name',       # used in -S valid_systems=
            'hostnames': ['login.*'],           # regex matching login node
            'modules_system': 'spack',          # or 'lmod', 'tmod'
            'stagedir': '/scratch/$USER/stage', # NOT on NFS home — avoids symlink issues
            'outputdir': '/scratch/$USER/output',
            'partitions': [
                {
                    'name': 'login',
                    'scheduler': 'local',
                    'launcher': 'local',
                    'environs': ['gnu', 'builtin'],
                    'extras': {'lfs_available': False},
                },
                {
                    'name': 'cpu',
                    'scheduler': 'slurm',
                    'launcher': 'srun',
                    'access': ['--partition=cpu'],
                    'environs': ['gnu', 'intel', 'foss'],
                    'extras': {'lfs_available': False},  # no lfs on cpu nodes
                },
                {
                    'name': 'gpu',
                    'scheduler': 'slurm',
                    'launcher': 'srun',
                    'access': ['--partition=gpu', '--gres=gpu:1'],
                    'environs': ['gnu'],
                    'extras': {'lfs_available': True},   # gpu nodes have lfs client
                },
            ],
        }
    ],
}
```

> **Important:** The `extras: lfs_available` flag controls whether `lustre_health_check`
> runs full `lfs df` / `lfs check` commands on a partition. Set to `True` only on
> partitions where the Lustre client tools (`lfs`) are installed and in `$PATH`.

---

## Customisation

### Adapting mount option requirements

Edit `fs_ref_opts` in `filesystem_options_check` to match your cluster's actual
mount options. To find the real options on your nodes:

```bash
# CPU node
srun --partition=cpu --nodes=1 --ntasks=1 \
  bash -c "awk '\$3~/lustre|nfs|ext4|xfs/ {print \$2,\$3,\$4}' /proc/mounts"

# GPU node
srun --partition=gpu --nodes=1 --ntasks=1 --gres=gpu:1 \
  bash -c "awk '\$3~/lustre|nfs|ext4|xfs/ {print \$2,\$3,\$4}' /proc/mounts"
```

Then update the dict:

```python
fs_ref_opts = variable(typ.Dict, loggable=True, value={
    'lustre': 'rw,flock,lazystatfs,encrypt',   # your actual options here
    'nfs4':   'rw,relatime',
    # add/remove types as needed
})
```

### Changing required mount points

```python
required_mounts = variable(typ.List[str], loggable=True,
                           value=['/home', '/scratch', '/project'])
```

### Changing probe paths for rw check

```python
probe_paths = variable(typ.List[str], loggable=True,
                       value=['/home', '/scratch', '/project'])
```

### Adjusting the bandwidth test size

The default writes 4 GB (4096 × 1M blocks). For a quick smoke run reduce the count:

```bash
# Quick 256 MB test
reframe ... -S scratch_io_bandwidth.count=256 -r

# Large 16 GB baseline measurement
reframe ... -S scratch_io_bandwidth.count=16384 -r
```

### Setting performance baselines (optional)

Once you have consistent baseline numbers, add references to fail on regression.
Add to `scratch_io_bandwidth`:

```python
@run_before('performance')
def set_reference(self):
    self.reference = {
        'your_cluster:cpu': {
            'write_bw': (1.6, -0.20, None, 'GB/s'),  # fail if drops >20%
            'read_bw':  (7.7, -0.20, None, 'GB/s'),
        },
        'your_cluster:gpu': {
            'write_bw': (1.6, -0.20, None, 'GB/s'),
            'read_bw':  (7.7, -0.20, None, 'GB/s'),
        },
    }
```

---

## Running selectively

```bash
# Only mount options check (fastest — no job submission)
./ci/rfm.sh -c hpctestlib/system/fs/mnt_opts.py \
  --tag gate -n filesystem_options_check -r

# Only smoke tests (options + rw — skips bandwidth measurement)
./ci/rfm.sh -c hpctestlib/system/fs/mnt_opts.py \
  --tag smoke -r

# Full filesystem suite including bandwidth
./ci/rfm.sh -c hpctestlib/system/fs/mnt_opts.py \
  --tag fs -r

# Dry run — shows what would be submitted without submitting
./ci/rfm.sh -c hpctestlib/system/fs/mnt_opts.py --dry-run
```

---

## Post-maintenance validation

After any system maintenance (node reboot, Lustre server restart, network change),
run the smoke subset — it completes in under 5 minutes:

```bash
# All partitions, smoke tests only
for partition in login cpu hm gpu; do
  echo "=== Testing $partition ==="
  ./ci/rfm.sh \
    -c hpctestlib/system/fs/mnt_opts.py \
    -S valid_systems=paramrudra.snbose:${partition} \
    -S valid_prog_environs=gnu \
    --tag smoke -r
done
```

---

## Troubleshooting

### `required variable 'fs_ref_opts' has not been set`
The variable declaration is missing a `value=` default. Ensure you are using the
current version of `mnt_opts.py` — run `grep 'value={' mnt_opts.py` and confirm
the dict is present.

### `not enough values to unpack (expected 6, got 1)`
A line in `/proc/mounts` did not have 6 fields. The current version guards against
this with `if len(fields) != 6: continue`. Ensure you are running the latest file.

### `Permission denied: /home/.rfm_probe_<jobid>`
The probe was writing to the root of `/home` instead of `$USER`'s subdirectory.
The current version uses `/home/$USER/.rfm_probe_...`. Ensure you have the latest file.

### `health check script did not complete`
The bash script is not executing on the compute node. Causes:
- `stagedir` is on NFS and the compute node cannot reach it — move stagedir to `/scratch`
- The script file was not written before the job ran — check `lfs_health.sh` exists
  in the stage directory

### `lfs commands did not complete — is lfs available?`
The `lfs` binary is not in `$PATH` on that partition. Either:
- Set `extras: {'lfs_available': False}` for that partition in `pseudo-cluster/settings.py`
- Or load the Lustre client module in the partition's `modules` list

### `build error: No makefile found`
`scratch_io_bandwidth` is incorrectly inheriting from `rfm.RegressionTest` instead of
`rfm.RunOnlyRegressionTest`. Check the class definition:
```bash
grep 'class scratch_io_bandwidth' hpctestlib/system/fs/mnt_opts.py
# Should show: class scratch_io_bandwidth(rfm.RunOnlyRegressionTest)
```

### Symlink loop error on stage directory
```
OSError: [Errno 40] Too many levels of symbolic links
```
Your `stagedir` is on NFS and Spack created a circular symlink. Move stagedir to
local scratch in `pseudo-cluster/settings.py`:
```python
'stagedir': '/scratch/$USER/stage',
'outputdir': '/scratch/$USER/output',
```

---

## Graylog integration (optional)

To stream test results to Graylog for centralised monitoring, add a GELF handler
to `config/common/settings.py`:

```python
'logging': [
    {
        'handlers': [
            # ... existing handlers ...
            {
                'type': 'gelf',
                'address': 'graylog.yourcluster.local',
                'port': 12201,
                'level': 'info',
                'extras': {
                    'cluster': 'paramrudra',
                    'suite':   'HPC_Test_Suite',
                    'stage':   'filesystem',
                },
            },
        ],
        'handlers_perflog': [
            {
                'type': 'gelf',
                'address': 'graylog.yourcluster.local',
                'port': 12201,
                'level': 'info',
                'extras': {
                    'log_type':  'performance',
                    'cluster':   'paramrudra',
                    'perf_var':  '%(check_perf_var)s',
                    'perf_val':  '%(check_perf_value)s',
                    'perf_unit': '%(check_perf_unit)s',
                },
            },
        ],
    }
],
```

Recommended Graylog streams to create:

| Stream name | Filter | Purpose |
|---|---|---|
| `hpc-fs-failures` | `level >= ERROR AND stage:filesystem` | Alert on gate failures |
| `hpc-fs-perf` | `log_type:performance AND stage:filesystem` | Bandwidth trend dashboard |
| `hpc-smoke` | `tags:smoke` | Post-maintenance quick check history |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-change`
3. Test your changes on at least one partition: `./ci/rfm.sh -c hpctestlib/system/fs/ --dry-run`
4. Commit with a clear message: `git commit -m "feat: add XFS stripe check"`
5. Open a pull request

### Adding a new filesystem check

All new tests should:
- Inherit from `rfm.RunOnlyRegressionTest` if there is nothing to compile
- Declare `valid_systems = ['*']` and `valid_prog_environs = ['builtin']`
- Include at least one tag from: `smoke`, `gate`, `perf`, `fs`, `lustre`
- Set `time_limit` explicitly
- Write bash scripts to files in `self.stagedir` rather than passing via `-c`
- Use `set +e` at the top of bash scripts so all commands run independently

---

## Licence

Copyright 2016-2024 Swiss National Supercomputing Centre (CSCS/ETH Zurich) — original
`filesystem_options_check` test.

Extensions copyright HPC_Test_Suite contributors.

SPDX-License-Identifier: BSD-3-Clause