import os
import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture
from spack_build import spack_ensure


class fetch_triton(rfm.RunOnlyRegressionTest):
    '''Fixture for fetching the Triton code from ORNL.'''
    local = True
    executable = 'git clone https://code.ornl.gov/hydro/triton.git'

    @sanity_function
    def validate_download(self):
        return sn.assert_eq(self.job.exitcode, 0)


@rfm.simple_test
class build_triton(rfm.CompileOnlyRegressionTest):
    '''Build Triton mini-app (OMP or CUDA variant).'''
    build_type = parameter(['hpc_omp', 'hpc_gpu'])
    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    tags = {'sciapp', 'triton', 'cpu', 'gpu'}
    build_system = 'Make'
    build_prefix = variable(str)
    build_locally = True
    triton_benchmarks = fixture(fetch_triton, scope='session')

    @run_before('compile')
    def prepare_build(self):
        fullpath = os.path.join(self.triton_benchmarks.stagedir, 'triton')
        self.prebuild_cmds += [
            f'cp -r {fullpath} {self.stagedir}',
            'cd triton',
        ]
        nvhpc_prefix = ''
        try:
            result = os.popen('spack find --loaded -p nvhpc 2>/dev/null').read().split()
            if result:
                nvhpc_prefix = result[-1]
        except Exception:
            pass
        if not nvhpc_prefix:
            nvhpc_prefix = spack_ensure('nvhpc@24.3')

        if self.build_type == 'hpc_omp':
            self.build_system.cc = 'mpic++'
            self.build_system.options = [
                'hpc_omp',
                f'INC_DIRS={nvhpc_prefix}/Linux_x86_64/24.3/comm_libs/11.8/hpcx/hpcx-2.14/ompi/include',
                f'LIBRARIES=-L{nvhpc_prefix}/Linux_x86_64/24.3/comm_libs/11.8/hpcx/hpcx-2.14/ompi/lib',
            ]
        if self.build_type == 'hpc_gpu':
            self.build_system.cc = 'nvcc'
            self.build_system.options = [
                'hpc_gpu',
                f'INC_DIRS={nvhpc_prefix}/Linux_x86_64/24.3/comm_libs/11.8/hpcx/hpcx-2.14/ompi/include',
                f'LIBRARIES=-L{nvhpc_prefix}/Linux_x86_64/24.3/comm_libs/11.8/hpcx/hpcx-2.14/ompi/lib',
                f'CUDA_HOME={nvhpc_prefix}/Linux_x86_64/24.3/cuda/11.8',
            ]

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @sanity_function
    def validate_build(self):
        return True
