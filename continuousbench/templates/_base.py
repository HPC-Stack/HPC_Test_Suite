# ContinuousBench template base classes.
# Select the appropriate base for your benchmark pattern.

import reframe as rfm
import reframe.utility.sanity as sn
from reframe.core.backends import getlauncher


class SingleNodeThroughput(rfm.RunOnlyRegressionTest):
    '''Template: single-node throughput benchmark (nightly microbenchmark).'''

    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    num_tasks = 1
    num_tasks_per_node = 1
    time_limit = '10m'

    @sanity_function
    def assert_exit_zero(self):
        return sn.assert_eq(self.job.exitcode, 0)


class StrongScalingBenchmark(rfm.RunOnlyRegressionTest):
    '''Template: strong-scaling sweep across N nodes.'''

    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    num_nodes = parameter([1, 2, 4, 8, 16])
    time_limit = '30m'

    @run_before('run')
    def set_tasks_from_nodes(self):
        self.num_tasks = self.num_nodes * self.num_tasks_per_node

    @sanity_function
    def assert_exit_zero(self):
        return sn.assert_eq(self.job.exitcode, 0)


class WeakScalingBenchmark(rfm.RunOnlyRegressionTest):
    '''Template: weak-scaling sweep (per-node work constant).'''

    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    num_nodes = parameter([1, 2, 4, 8, 16])
    time_limit = '30m'

    @run_before('run')
    def set_tasks_from_nodes(self):
        self.num_tasks = self.num_nodes * self.num_tasks_per_node

    @sanity_function
    def assert_exit_zero(self):
        return sn.assert_eq(self.job.exitcode, 0)


class GpuOccupancyBenchmark(rfm.RunOnlyRegressionTest):
    '''Template: GPU occupancy / GPU compute benchmark.'''

    valid_systems = ['*:gpu']
    valid_prog_environs = ['gnu']
    num_gpus_per_node = 1
    time_limit = '10m'

    @sanity_function
    def assert_exit_zero(self):
        return sn.assert_eq(self.job.exitcode, 0)


class CommunicationStress(rfm.RunOnlyRegressionTest):
    '''Template: MPI communication stress test.'''

    valid_systems = ['*']
    valid_prog_environs = ['gnu']
    num_nodes = parameter([1, 2, 4, 8])
    time_limit = '10m'

    @run_before('run')
    def setup_launcher(self):
        self.job.launcher = getlauncher('srun')()
        self.num_tasks = self.num_nodes * 2

    @sanity_function
    def assert_exit_zero(self):
        return sn.assert_eq(self.job.exitcode, 0)
