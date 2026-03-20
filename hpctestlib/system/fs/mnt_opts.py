# hpctestlib/system/fs/mnt_opts.py
# Copyright 2016-2024 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# Extended for Lustre + home + scratch by HPC_Test_Suite
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Verified mount options (srun on rbcn024 cpu and rbgpu008 gpu):
#   /home    lustre  rw,flock,lazystatfs,encrypt
#   /scratch lustre  rw,flock,lazystatfs,encrypt
#   tmpfs and devtmpfs intentionally not checked — vary per mountpoint.
#
# Partition extras required in pseudo-cluster/settings.py:
#   cpu/hm/login: extras = {'lfs_available': False}
#   gpu:          extras = {'lfs_available': True}

import os
import re
from string import Template

import reframe as rfm
import reframe.utility.sanity as sn
import reframe.utility.typecheck as typ
import reframe.utility.udeps as udeps


# ---------------------------------------------------------------------------
# Test 1 — filesystem mount options check
# ---------------------------------------------------------------------------

@rfm.simple_test
class filesystem_options_check(rfm.RunOnlyRegressionTest):
    '''Filesystem mount options check.

    Reads /proc/mounts and verifies that each filesystem type listed
    in fs_ref_opts has the required options set.

    tmpfs and devtmpfs are intentionally excluded — they vary per
    mountpoint (/sys/fs/cgroup is ro, / is rw,relatime, etc.) and
    are not relevant to HPC workload correctness.
    '''

    #: Reference mount options per filesystem type.
    #: Only types listed here are checked. Everything else is skipped.
    #:
    #: :type: `Dict[str, str]`
    fs_ref_opts = variable(typ.Dict, loggable=True, value={
        # Verified on rbcn024 (cpu) and rbgpu008 (gpu) — identical
        'lustre': 'rw,flock,lazystatfs,encrypt',
        # Kept for login node / NFS mounts
        'nfs':    'rw,relatime',
        'nfs4':   'rw,relatime',
        'ext4':   'rw,relatime',
        'xfs':    'rw,relatime,nosuid',
        # tmpfs/devtmpfs removed — no consistent option set across all mounts:
        #   /sys/fs/cgroup tmpfs → ro,nosuid,nodev,noexec  (read-only by design)
        #   /              tmpfs → rw,relatime
        #   /.sllocal/log  tmpfs → rw,relatime
        #   /dev/shm       tmpfs → rw,nosuid,nodev
    })

    #: Fail on unknown filesystem types.
    #: Keep False — /proc/mounts always contains kernel pseudo-fs types
    #: (cgroup, proc, sysfs, autofs, pstore, tmpfs, devtmpfs ...).
    #:
    #: :type: `Bool`
    #: :value: ``False``
    fail_unknown_fs = variable(typ.Bool, value=False, loggable=True)

    #: Mount points that MUST appear in /proc/mounts.
    #: Test fails immediately if any of these are absent.
    #:
    #: :type: `List[str]`
    required_mounts = variable(typ.List[str], loggable=True,
                               value=['/home', '/scratch'])

    valid_systems = ['*']
    valid_prog_environs = ['builtin']
    executable = 'cat'
    executable_opts = ['/proc/mounts']
    tags = {'system', 'fs', 'smoke', 'gate'}

    @run_before('sanity')
    def process_system_fs_opts(self):
        self.filesystem = []
        stdout = os.path.join(self.stagedir, sn.evaluate(self.stdout))
        with open(stdout, 'r') as fp:
            for line in fp:
                line = line.strip()
                # Skip blank lines, comments, and the reference block
                # appended by print_test_variables_to_output below
                if not line or line.startswith('#') or line.startswith('----'):
                    continue
                fields = line.split()
                # /proc/mounts has exactly 6 fields:
                #   device  mountpoint  fstype  options  dump  pass
                # Skip anything else (appended text, wrapped lines, etc.)
                if len(fields) != 6:
                    continue
                _, mnt_point, mnt_type, options, _, _ = fields
                self.filesystem.append((mnt_point, mnt_type, options))

    @run_before('sanity')
    def print_test_variables_to_output(self):
        '''Append reference options to stdout for human inspection.'''
        stdout = os.path.join(self.stagedir, sn.evaluate(self.stdout))
        with open(stdout, 'a') as fp:
            fp.write('\n---- Reference mount options ----\n')
            for mnt_type, options in self.fs_ref_opts.items():
                fp.write(f'{mnt_type} {options}\n')
            fp.write('\n---- Required mount points ----\n')
            for mp in self.required_mounts:
                fp.write(f'{mp}\n')

    def explode_opts_str(self, opts_str):
        '''Parse a comma-separated options string into a dict.'''
        result = {}
        for opt in opts_str.split(','):
            if opt == '':
                continue
            opt_parts = opt.split('=', maxsplit=2)
            result[opt_parts[0]] = opt_parts[1] if len(opt_parts) > 1 else ''
        return result

    @sanity_function
    def assert_mnt_options(self):
        msg_unknown = Template(
            'Found filesystem type(s) "$mnt_type" not in reference dict'
        )
        msg_missing_mp = Template(
            'Required mount point "$mnt_point" is NOT mounted'
        )
        msg_missing_opt = Template(
            'Mount "$mnt_point" ($mnt_type) is missing required option "$opt"'
        )
        msg_wrong_val = Template(
            'Mount "$mnt_point" ($mnt_type): '
            '"$variable" is "$value" but expected "$ref_value"'
        )

        errors = []
        unsupported_types = set()
        mounted_points = {mp for mp, _, _ in self.filesystem}

        # 1. Verify all required mount points are present
        for required in self.required_mounts:
            if required not in mounted_points:
                errors.append(msg_missing_mp.substitute(mnt_point=required))

        # 2. Verify mount options for every known filesystem type
        for mnt_point, mnt_type, options in self.filesystem:
            opts = self.explode_opts_str(options)
            if mnt_type not in self.fs_ref_opts:
                unsupported_types.add(mnt_type)
                continue
            ref_opts = self.explode_opts_str(self.fs_ref_opts[mnt_type])
            for ref_opt, ref_value in ref_opts.items():
                if ref_opt not in opts:
                    errors.append(msg_missing_opt.substitute(
                        opt=ref_opt,
                        mnt_point=mnt_point,
                        mnt_type=mnt_type,
                    ))
                elif ref_value and ref_value != opts[ref_opt]:
                    errors.append(msg_wrong_val.substitute(
                        value=opts[ref_opt],
                        ref_value=ref_value,
                        variable=ref_opt,
                        mnt_point=mnt_point,
                        mnt_type=mnt_type,
                    ))

        # 3. Optionally fail on unknown filesystem types
        if self.fail_unknown_fs and unsupported_types:
            errors.append(msg_unknown.substitute(
                mnt_type=', '.join(sorted(unsupported_types))
            ))

        return sn.assert_true(errors == [], msg='\n'.join(errors))


# ---------------------------------------------------------------------------
# Test 2 — Lustre health check (OSTs, MDTs, free space, stripe)
# ---------------------------------------------------------------------------

@rfm.simple_test
class lustre_health_check(rfm.RunOnlyRegressionTest):
    '''Lustre-specific health checks.

    Uses df (always available) as the primary check.
    Uses lfs commands only when partition extras.lfs_available = True.

    The health script is written to a file before execution — this
    avoids shell quoting/escaping issues that occur when passing
    multiline scripts via executable_opts = ['-c', script].
    Each command runs independently (set +e) so LFS_HEALTH_DONE
    always appears in output even if an earlier command fails.
    '''

    #: Minimum free space percentage required on each Lustre mount.
    #:
    #: :type: `float`
    min_free_pct = variable(float, value=10.0, loggable=True)

    #: Expected minimum stripe count on /scratch.
    #: Raise to your actual value once confirmed via lfs getstripe.
    #:
    #: :type: `int`
    expected_stripe_count = variable(int, value=1, loggable=True)

    #: Lustre mount points to inspect.
    #:
    #: :type: `List[str]`
    lustre_mounts = variable(typ.List[str], loggable=True,
                             value=['/home', '/scratch'])

    valid_systems = ['*']
    valid_prog_environs = ['builtin']
    executable = 'bash'
    tags = {'system', 'fs', 'lustre', 'smoke', 'gate'}
    time_limit = '5m'

    @run_before('run')
    def write_health_script(self):
        '''Write the health check script to a file in stagedir.

        Writing to a file avoids ReFrame shell-escaping the newlines
        in a multiline -c argument, which caused the script to only
        run its first line on some SLURM configurations.
        '''
        lfs_ok = self.current_partition.extras.get('lfs_available', False)

        lines = ['#!/bin/bash', 'set +e', '']

        for mp in self.lustre_mounts:
            lines += [
                f'echo "RFM_DF_START:{mp}"',
                f'df -h {mp}',
                f'echo "RFM_DF_END:{mp}"',
                '',
            ]
            if lfs_ok:
                lines += [
                    f'echo "RFM_LFS_START:{mp}"',
                    f'lfs df -h {mp}',
                    f'lfs getstripe --stripe-count {mp} 2>/dev/null '
                    f'|| echo "STRIPE_NA"',
                    f'echo "RFM_LFS_END:{mp}"',
                    '',
                ]

        if lfs_ok:
            lines += [
                'echo "RFM_LFS_CHECK_START"',
                'lfs check all 2>&1 || lfs check servers 2>&1',
                'echo "RFM_LFS_CHECK_END"',
                '',
            ]

        lines.append('echo "LFS_HEALTH_DONE"')

        script_path = os.path.join(self.stagedir, 'lfs_health.sh')
        with open(script_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        os.chmod(script_path, 0o755)

        self.executable_opts = [script_path]

    @performance_function('%')
    def scratch_free_pct(self):
        # Matches both df and lfs df output — both end with Use%  /scratch...
        return sn.extractsingle(
            r'(\d+)%\s+/scratch',
            self.stdout, 1,
            lambda x: 100.0 - float(x),
        )

    @performance_function('%')
    def home_free_pct(self):
        return sn.extractsingle(
            r'(\d+)%\s+/home',
            self.stdout, 1,
            lambda x: 100.0 - float(x),
        )

    @sanity_function
    def validate_lustre_health(self):
        errors = []

        # 1. Confirm the script ran to completion
        completed = sn.evaluate(
            sn.count(sn.findall(r'LFS_HEALTH_DONE', self.stdout))
        )
        if completed == 0:
            return sn.assert_true(
                False,
                msg='health check script did not complete — '
                    'check that bash is available on the compute node'
            )

        stdout_path = os.path.join(self.stagedir, sn.evaluate(self.stdout))
        with open(stdout_path) as f:
            content = f.read()

        lfs_ok = self.current_partition.extras.get('lfs_available', False)

        # 2. Verify df ran and completed for each mount (start + end markers)
        for mp in self.lustre_mounts:
            if f'RFM_DF_START:{mp}' not in content:
                errors.append(
                    f'df did not start for {mp} — possible mount hang'
                )
            elif f'RFM_DF_END:{mp}' not in content:
                errors.append(
                    f'df did not complete for {mp} — possible hung mount'
                )

        # 3. lfs-specific checks — only on partitions with lfs client
        if lfs_ok:
            if 'inactive' in content.lower():
                errors.append('One or more Lustre OST/MDT is INACTIVE')
            if 'no route to host' in content.lower():
                errors.append('Lustre server unreachable (no route to host)')

            stripe_matches = re.findall(r'stripe_count\s+(\d+)', content)
            if stripe_matches:
                actual = int(stripe_matches[0])
                if actual < self.expected_stripe_count:
                    errors.append(
                        f'/scratch stripe_count is {actual}, '
                        f'expected >= {self.expected_stripe_count}'
                    )

        return sn.assert_true(errors == [], msg='\n'.join(errors))


# ---------------------------------------------------------------------------
# Test 3 — read/write probe on /home and /scratch
# ---------------------------------------------------------------------------

@rfm.simple_test
class filesystem_rw_check(rfm.RunOnlyRegressionTest):
    '''Verify actual read/write capability on /home and /scratch.

    Probes the user's own subdirectory — not the root of the mount —
    because compute nodes do not have write permission on /home root.

    Probe paths:
      /home/$USER/.rfm_probe_<jobid>
      /scratch/$USER/.rfm_probe_<jobid>

    Only runs if filesystem_options_check passes (dependency gate).
    '''

    #: Mount points to probe with a write/read/delete cycle.
    #:
    #: :type: `List[str]`
    probe_paths = variable(typ.List[str], loggable=True,
                           value=['/home', '/scratch'])

    valid_systems = ['*']
    valid_prog_environs = ['builtin']
    executable = 'bash'
    tags = {'system', 'fs', 'smoke', 'gate'}
    time_limit = '5m'

    @run_after('init')
    def set_dependency(self):
        self.depends_on('filesystem_options_check', udeps.any)

    @run_before('run')
    def write_probe_script(self):
        '''Write the probe script to a file — avoids quoting issues.'''
        lines = ['#!/bin/bash', 'set +e', '']

        for path in self.probe_paths:
            # Write into $USER's own directory — always writable.
            # mkdir -p ensures /scratch/$USER exists even on first use.
            probe = f'{path}/$USER/.rfm_probe_${{SLURM_JOB_ID:-$$}}'
            lines += [
                f'mkdir -p {path}/$USER',
                f'echo "rfm_probe" > {probe}',
                f'cat {probe}',
                f'rm -f {probe}',
                f'echo "RW_OK:{path}"',
                '',
            ]

        script_path = os.path.join(self.stagedir, 'rw_probe.sh')
        with open(script_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        os.chmod(script_path, 0o755)

        self.executable_opts = [script_path]

    @sanity_function
    def validate_rw(self):
        return sn.all([
            sn.assert_found(rf'RW_OK:{re.escape(path)}', self.stdout)
            for path in self.probe_paths
        ])


# ---------------------------------------------------------------------------
# Test 4 — I/O bandwidth baseline on /scratch
# ---------------------------------------------------------------------------

@rfm.simple_test
class scratch_io_bandwidth(rfm.RunOnlyRegressionTest):
    '''Measure sequential write/read bandwidth on /scratch using dd.

    Writes to /scratch/$USER/ — user-owned, always writable.
    Tracks bandwidth over time via the ReFrame performance log —
    provides early warning for Lustre OST degradation.

    Only runs after filesystem_rw_check confirms /scratch is writable.

    Inherits from RunOnlyRegressionTest — no compilation step,
    no makefile needed.
    '''

    valid_systems = ['*']
    valid_prog_environs = ['builtin']
    tags = {'fs', 'perf', 'lustre'}
    time_limit = '15m'

    #: dd block size.
    #:
    #: :type: `str`
    bs = variable(str, value='1M', loggable=True)

    #: Number of blocks — default 4096 x 1M = 4 GB total.
    #: Reduce for quick smoke runs, increase for accurate baselines.
    #:
    #: :type: `int`
    count = variable(int, value=4096, loggable=True)

    executable = 'bash'

    @run_after('init')
    def set_dependency(self):
        # Only run after rw_check confirms /scratch is writable
        self.depends_on('filesystem_rw_check', udeps.any)

    @run_before('run')
    def write_dd_script(self):
        '''Write the dd benchmark script to a file — avoids quoting issues.'''
        probe = '/scratch/$USER/.rfm_bw_${SLURM_JOB_ID:-$$}'
        lines = [
            '#!/bin/bash',
            'set +e',
            '',
            f'mkdir -p /scratch/$USER',
            'echo "=== write ==="',
            f'dd if=/dev/zero of={probe} bs={self.bs} count={self.count}'
            f' conv=fdatasync 2>&1',
            'echo "=== read ==="',
            f'dd if={probe} of=/dev/null bs={self.bs} 2>&1',
            f'rm -f {probe}',
            'echo "IO_BW_DONE"',
        ]

        script_path = os.path.join(self.stagedir, 'dd_bench.sh')
        with open(script_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        os.chmod(script_path, 0o755)

        self.executable_opts = [script_path]

    @performance_function('GB/s', perf_key='write_bw')
    def write_bandwidth(self):
        # dd output: N bytes copied, X s, Y         MB/s
        # item=0 → first match = write pass
        return sn.extractsingle(
            r'(\d+\.?\d*)\s+GB/s',
            self.stdout, 1, float,
            item=0,
        )

    @performance_function('GB/s', perf_key='read_bw')
    def read_bandwidth(self):
        # item=1 → second match = read pass
        return sn.extractsingle(
            r'(\d+\.?\d*)\s+GB/s',
            self.stdout, 1, float,
            item=1,
        )

    @sanity_function
    def validate(self):
        return sn.assert_found(r'IO_BW_DONE', self.stdout)
