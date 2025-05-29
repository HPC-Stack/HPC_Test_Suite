import os
import shutil
import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher


class fetch_triton(rfm.RunOnlyRegressionTest):
    '''Fixture for fetching the Tritron code...'''
    
    #: The version of the benchmarks to fetch.
    #:
    #: :type: :class:`str`
    #: :default: ``'latest'``
    local = True
    executable = f'git clone https://code.ornl.gov/hydro/triton.git'

    @sanity_function
    def validate_download(self):
        return sn.assert_eq(self.job.exitcode, 0)

@rfm.simple_test
class build_tritron(rfm.CompileOnlyRegressionTest):
    '''Fixture for building the Tritron'''
    #: Build variant parameter.
    #:
    #: :type: :class:`str`
    #: :values: ``'hpc_omp', 'hpc_gpu'``
    build_type = parameter(['hpc_omp', 'hpc_gpu'])
    modules = ['gcc@13/3wdooxp','nvhpc/kykmjze']
    build_system = 'Make'
    build_prefix = variable(str)
    build_locally= True
    #: The fixture object that retrieves the code base
    #:
    #: :type: :class:`fetuch_triton`
    #: :scope: *session*
    triton_benchmarks = fixture(fetch_triton, scope='session')

    @run_before('compile')
    def prepare_build(self):        
        fullpath = os.path.join(self.triton_benchmarks.stagedir, 'triton')
        self.prebuild_cmds += [
            f'cp -r {fullpath} {self.stagedir}',
            f'cd triton'
        ]
        nvhpc_prefix = os.popen('spack find --loaded -p nvhpc').read().split()[-1]
        if self.build_type == 'hpc_omp':
            self.build_system.cc  = 'mpic++'
            self.build_system.options  = ['hpc_omp',
                                           f'INC_DIRS={nvhpc_prefix}/Linux_x86_64/24.3/comm_libs/11.8/hpcx/hpcx-2.14/ompi/include',
                                           f'LIBRARIES=-L{nvhpc_prefix}/Linux_x86_64/24.3/comm_libs/11.8/hpcx/hpcx-2.14/ompi/lib'
                                         ]
        if self.build_type == 'hpc_gpu':
            self.build_system.cc  = 'nvcc'
            self.build_system.options = ['hpc_gpu',
                                          f'INC_DIRS={nvhpc_prefix}/Linux_x86_64/24.3/comm_libs/11.8/hpcx/hpcx-2.14/ompi/include',
                                          f'LIBRARIES=-L{nvhpc_prefix}/Linux_x86_64/24.3/comm_libs/11.8/hpcx/hpcx-2.14/ompi/lib',
                                          f'CUDA_HOME={nvhpc_prefix}/Linux_x86_64/24.3/cuda/11.8'
                                        ]

    @sanity_function
    def validate_build(self):
        # If build fails, the test will fail before reaching this point.
        return True




