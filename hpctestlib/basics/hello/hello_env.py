# Pilot: Hello World with environment capture.
# Demonstrates env_snapshot.sh integration and tag-based selection.

import reframe as rfm
import reframe.utility.sanity as sn
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'continuousbench', 'hooks'))
from env_capture import add_env_capture


@rfm.simple_test
class HelloEnvTest(rfm.RegressionTest):
    descr = 'Hello World with environment provenance capture'
    valid_systems = ['*:cpu']
    valid_prog_environs = ['gnu']
    sourcesdir = 'src'
    sourcepath = 'hello.c'
    tags = {'smoke', 'cpu', 'basics', 'pilot'}

    @run_before('run')
    def setup_env_capture(self):
        add_env_capture(self)

    @sanity_function
    def assert_hello(self):
        return sn.assert_found(r'Hello, World\!', self.stdout)
