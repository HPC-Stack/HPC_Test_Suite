import os

paramrudra_snbose = {
    'name': 'paramrudra.snbose',
    'descr': 'paramrudra.snbose system',
    'hostnames': ['.*'],
    'modules_system': 'spack',
    'resourcesdir': "/home/apps/hpc_inputs/",
    'stagedir': os.path.join(os.getcwd(), 'stage'),
    'partitions': [
        {
            'name': 'login',
            'scheduler': 'local',
            'launcher': 'local',
            'environs': ['gnu', 'intel', 'foss', 'spack-only'],
        },
        {
            'name': 'cpu',
            'descr': 'cpu nodes',
            'scheduler': 'slurm',
            'launcher': 'srun',
            'access': ['--partition=cpu'],
            'environs': ['gnu', 'intel', 'foss', 'spack-only'],
            'max_jobs': 100,
            'processor': {
                'num_cpus': 48,
                'num_sockets': 2,
                'num_cpus_per_socket': 24
            },
            'resources': [
                {
                    'name': 'memory',
                    'options': ['--mem={size}', '--time=10:00:00']
                }
            ]
        },
        {
            'name': 'hm',
            'descr': 'hm nodes',
            'scheduler': 'slurm',
            'launcher': 'srun',
            'access': ['--partition=hm'],
            'environs': ['gnu', 'intel', 'spack-only'],
            'max_jobs': 100,
            'processor': {
                'num_cpus': 48,
                'num_sockets': 2,
                'num_cpus_per_socket': 24
            },
            'resources': [
                {
                    'name': 'memory',
                    'options': ['--mem={size}', '--time=10:00:00']
                }
            ]
        },
        {
            'name': 'gpu',
            'descr': 'gpu nodes',
            'modules': ['cuda@12.5.1/7zllz27'],
            'scheduler': 'slurm',
            'launcher': 'srun',
            'access': ['--partition=gpu', '--gres=gpu:2', '--time=10:00:00'],
            'environs': ['gnu', 'spack-only'],
            'max_jobs': 100,
            'processor': {
                'num_cpus': 48,
                'num_sockets': 2,
                'num_cpus_per_socket': 24
            },
            'resources': [
                {
                    'name': 'memory',
                    'options': ['--mem={size}']
                }
            ]
        },
    ]
}
