#!/bin/bash
# Environment snapshot for ContinuousBench
# Writes JSON sidecar alongside each benchmark result.
# Uses Python for reliable JSON encoding.

set -euo pipefail

OUTPUT="${1:-env_snapshot.json}"
PYTHON="${PYTHON:-python3}"

"$PYTHON" -c "
import json, os, subprocess, sys

env = {}

env['timestamp'] = __import__('datetime').datetime.now().isoformat()
env['hostname'] = os.uname().nodename
env['kernel'] = os.uname().release

# Modules
try:
    r = subprocess.run(['module', 'list'], capture_output=True, text=True, timeout=10)
    mods = r.stdout.strip().split('\n')[3:] if r.stdout else []
    env['modules'] = [m.strip() for m in mods if m.strip() and not m.startswith('No')]
except Exception:
    env['modules'] = []

# SLURM env
slurm = {}
for var in ['SLURM_JOB_ID','SLURM_NODELIST','SLURM_CPUS_ON_NODE',
            'SLURM_JOB_NUM_NODES','SLURM_NTASKS','SLURM_NTASKS_PER_NODE',
            'SLURM_CPU_BIND','SLURM_PARTITION']:
    val = os.environ.get(var, '')
    if val: slurm[var] = val

# CPU
try:
    with open('/proc/cpuinfo') as f:
        cpuinfo = f.read()
    cpu = {}
    for line in cpuinfo.strip().split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            k, v = k.strip(), v.strip()
            if k == 'model name' and 'model' not in cpu:
                cpu['model'] = v
            elif k == 'physical id' and 'sockets' not in cpu:
                cpu.setdefault('sockets', set()).add(v)
    if 'sockets' in cpu:
        cpu['sockets'] = len(cpu['sockets'])
    cpu['cores'] = os.cpu_count() or os.sysconf('SC_NPROCESSORS_ONLN')
    env['cpu'] = cpu
except Exception:
    env['cpu'] = {}

# Memory
try:
    with open('/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemTotal'):
                env['memory'] = {'total': line.split()[1] + ' ' + line.split()[2]}
                break
except Exception:
    env['memory'] = {}

# GPU via nvidia-smi
gpus = []
try:
    r = subprocess.run(['nvidia-smi','--query-gpu=index,name,driver_version,memory.total',
                        '--format=csv,noheader,nounits'],
                       capture_output=True, text=True, timeout=10)
    for line in r.stdout.strip().split('\n'):
        if not line.strip(): continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 4:
            gpus.append({'index': int(parts[0]), 'name': parts[1],
                         'driver': parts[2], 'memory_mb': parts[3]})
except Exception:
    pass
env['gpu'] = gpus

# MPI version
try:
    r = subprocess.run(['mpirun','--version'], capture_output=True, text=True, timeout=10)
    env['mpi'] = r.stdout.strip().split('\n')[0] if r.stdout else ''
except Exception:
    env['mpi'] = ''

# Libraries (key dynamic libs)
libs = {}
try:
    r = subprocess.run(['ldconfig', '-p'], capture_output=True, text=True, timeout=10)
    for target in ['libmpi.so', 'libcuda.so', 'libcudart.so', 'libopenblas.so']:
        for line in r.stdout.split('\n'):
            if target in line and target not in libs:
                parts = line.strip().split()
                if len(parts) >= 2:
                    libs[target] = parts[-1]
                break
except Exception:
    pass
env['libraries'] = libs

env['slurm'] = slurm

with open('$OUTPUT', 'w') as f:
    json.dump(env, f, indent=2)

print(f'Environment snapshot written to $OUTPUT')
"
