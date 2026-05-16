# Environment capture utility for ContinuousBench.
# Provides a function to add env_snapshot.sh as a postrun command.
# Call from any test's @run_before('run') hook.

import os


def add_env_capture(test):
    '''Add env_snapshot.sh as a postrun command and preserve the output.

    Call this from a @run_before('run') hook in your ReFrame test:
        @run_before('run')
        def setup_env_capture(self):
            add_env_capture(self)
    '''
    script_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 'scripts', 'env_snapshot.sh'
    )
    script_path = os.path.abspath(script_path)
    output_file = f'env_snapshot_{test.name}.json'

    # Add postrun command to capture env on the compute node
    current = list(getattr(test, 'postrun_cmds', None) or [])
    current.append(f'bash {script_path} {output_file}')
    test.postrun_cmds = current

    # Preserve the env_snapshot JSON after job cleanup
    kept = list(getattr(test, 'keep_files', None) or [])
    kept.append(output_file)
    test.keep_files = kept
