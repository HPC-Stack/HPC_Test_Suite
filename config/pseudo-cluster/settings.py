# config/multifile/pseudo-cluster/settings.py
# System definition for paramrudra.snbose
# Rename this directory to match your actual cluster name if desired.

import os

site_configuration = {
    'systems': [
        {
            'name': 'paramrudra.snbose',
            'descr': 'Param Rudra cluster — SNBOSE',
            'hostnames': ['.*'],
            'modules_system': 'spack',
            'resourcesdir': '/home/apps/hpc_inputs/',
            'stagedir': '/scratch/$USER/reframe/stage',
            'outputdir': '/scratch/$USER/reframe/output',
            'partitions': [
                {
                    'name': 'login',
                    'extras': {'lfs_available': False},
                    'descr': 'Login node — local execution',
                    'scheduler': 'local',
                    'launcher': 'local',
                    'environs': ['gnu', 'intel', 'foss', 'spack-only', 'builtin'],
                },
                {
                    'name': 'cpu',
                    'descr': 'CPU compute nodes',
                    'extras': {'lfs_available': False},
                    'scheduler': 'slurm',
                    'launcher': 'srun',
                    'access': ['--partition=cpu'],
                    'environs': ['gnu', 'intel', 'foss', 'spack-only'],
                    'max_jobs': 100,
                    'processor': {
                        'num_cpus': 48,
                        'num_sockets': 2,
                        'num_cpus_per_socket': 24,
                    },
                    'resources': [
                        {
                            'name': 'memory',
                            'options': ['--mem={size}', '--time=10:00:00'],
                        }
                    ],
                },
                {
                    'name': 'hm',
                    'descr': 'High-memory nodes',
                    'extras': {'lfs_available': False},
                    'scheduler': 'slurm',
                    'launcher': 'srun',
                    'access': ['--partition=hm'],
                    'environs': ['gnu', 'intel', 'spack-only'],
                    'max_jobs': 100,
                    'processor': {
                        'num_cpus': 48,
                        'num_sockets': 2,
                        'num_cpus_per_socket': 24,
                    },
                    'resources': [
                        {
                            'name': 'memory',
                            'options': ['--mem={size}', '--time=10:00:00'],
                        }
                    ],
                },
                {
                    'name': 'gpu',
                    'descr': 'GPU nodes — NVIDIA',
                    'extras': {'lfs_available': True},
                    'modules': ['cuda@12.5.1/klbpcme'],
                    'scheduler': 'slurm',
                    'launcher': 'srun',
                    'access': [
                        '--partition=gpu',
                        '--gres=gpu:2',
                        '--time=10:00:00',
                    ],
                    'environs': ['gnu', 'foss','spack-only'],
                    'max_jobs': 100,
                    'features': ['gpu', 'cuda'],       # ← added for skip_unless_any_features
                    'processor': {
                        'num_cpus': 48,
                        'num_sockets': 2,
                        'num_cpus_per_socket': 24,
                    },
                    'resources': [
                        {
                            'name': 'memory',
                            'options': ['--mem={size}'],
                        }
                    ],
                },
            ],
        }
    ],
}