import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import glob
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure


def parse_time_cmd(s):
    mins, _, secs = s.strip().partition('m')
    return float(mins) * 60.0 + float(secs.rstrip('s'))


@rfm.simple_test
class openfoamTest(rfm.RunOnlyRegressionTest):
    descr = 'OpenFOAM CPU benchmark — simpleFoam (para)'
    np = parameter([48, 96, 192, 384])
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'cfd', 'openfoam', 'cpu'}
    sourcesdir = '/home/apps/hpc_inputs/applications/OPENFOAM'
    exclusive_access = True
    modules = ['intel-oneapi-mpi/r4bynxk','openfoam/32llhjn']
    env_vars = {'OMP_NUM_THREADS': '1'}

    reference = {
        '*': {
            'ExecutionTime': (0, None, None, 's'),
            'ClockTime': (0, None, None, 's'),
            'runtime_real': (0, None, None, 's'),
        }
    }

    executable = 'simpleFoam'
    keep_files = ['log.snappyHexMesh', 'log.blockMesh', 'log.decomposePar']

    @run_before('run')
    def set_num_task(self):
        self.num_tasks = self.np
        self.executable_opts = ["-parallel"] if self.num_tasks > 1 else [""]
        self.prerun_cmds = [
            'tar --strip-components 2 -xf Motorbike_bench_template.tar.gz bench_template/basecase',
            './Allclean',
            f'sed -i -- "s/method .*/method          scotch;/g" system/decomposeParDict',
            f'sed -i -- "s/numberOfSubdomains .*/numberOfSubdomains {self.num_tasks};/g" system/decomposeParDict',
            'sed -i -- \'s/    #include "streamLines"//g\' system/controlDict',
            'sed -i -- \'s/    #include "wallBoundedStreamLines"//g\' system/controlDict',
            "sed -i -- 's|caseDicts|caseDicts/mesh/generation|' system/meshQualityDict ",
            './Allmesh',
            'time \\',
        ]

    @run_before('run')
    def replace_launcher(self):
        self.job.launcher = getlauncher('mpirun')()

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @run_before('run')
    def ensure_spack(self):
        prefix = spack_ensure('openfoam@2312')
        if prefix:
            for d in ['bin', 'platforms/*/bin']:
                for p in glob.glob(os.path.join(prefix, d)):
                    if os.path.isdir(p):
                        self.env_vars['PATH'] = f'{p}:$PATH'

    @sanity_function
    def validate_program(self):
        return sn.assert_eq(self.job.exitcode, 0)

    @performance_function('s', perf_key='ExecutionTime')
    def extract_ExecutionTime(self):
        matches = sn.extractall(r'ExecutionTime = ([\d.]+) s  ClockTime = ([\d.]+) s', self.stdout, 1, float)
        return matches[-1] if matches else 0.0

    @performance_function('s', perf_key='ClockTime')
    def extract_ClockTime(self):
        matches = sn.extractall(r'ExecutionTime = ([\d.]+) s  ClockTime = ([\d.]+) s', self.stdout, 2, float)
        return matches[-1] if matches else 0.0

    @performance_function('s', perf_key='runtime_real')
    def extract_runtime_real(self):
        return sn.extractsingle(r'^real\s+(\d+m[\d.]+s)$', self.stderr, 1, parse_time_cmd)
# rfmdocend: echorand
