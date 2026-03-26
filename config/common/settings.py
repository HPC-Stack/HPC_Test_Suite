# config/multifile/common/settings.py
# Shared logging and general settings for all systems.
# Pass this file first in every -C invocation.

site_configuration = {
    'general': [
        {
            'check_search_path': [
                './application',
                './basics',
                './hpctestlib',
            ],
            'check_search_recursive': True,
            'remote_detect': False,
            'purge_environment': True,
            'report_file': './reports/run-report-{sessionid}.json',
        }
    ],

    'logging': [
        {
            'handlers': [
                {
                    'type': 'stream',
                    'name': 'stdout',
                    'level': 'info',
                    'format': '%(message)s',
                },
                {
                    'type': 'file',
                    'level': 'debug2',
                    'format': (
                        '[%(asctime)s] %(levelname)s: '
                        '%(check_info)s: %(message)s'
                    ),
                    'append': False,
                },
                # --- Graylog GELF handler (add your server address) ---
                # {
                #     'type': 'gelf',
                #     'address': 'graylog.yourcluster.local',
                #     'port': 12201,
                #     'level': 'info',
                #     'extras': {
                #         'cluster': 'paramrudra',
                #         'suite':   'HPC_Test_Suite',
                #     },
                # },
            ],
            'handlers_perflog': [
                {
                    'type': 'filelog',
                    'prefix': '%(check_system)s/%(check_partition)s',
                    'level': 'info',
                    'format': (
                        '%(check_job_completion_time)s,'
                        'reframe %(version)s,'
                        '%(check_info)s,'
                        'jobid=%(check_jobid)s,'
                        '%(check_perf_var)s=%(check_perf_value)s,'
                        'num_tasks=%(check_num_tasks)s,'
                        'num_tasks_per_node=%(check_num_tasks_per_node)s,'
                        'ref=%(check_perf_ref)s '
                        '(l=%(check_perf_lower_thres)s,'
                        'u=%(check_perf_upper_thres)s),'
                        '%(check_perf_unit)s'
                    ),
                    'append': True,
                },
                # --- Graylog perf log (uncomment when Graylog is ready) ---
                # {
                #     'type': 'gelf',
                #     'address': 'graylog.yourcluster.local',
                #     'port': 12201,
                #     'level': 'info',
                #     'extras': {
                #         'log_type':  'performance',
                #         'cluster':   'paramrudra',
                #         'perf_var':  '%(check_perf_var)s',
                #         'perf_val':  '%(check_perf_value)s',
                #         'perf_unit': '%(check_perf_unit)s',
                #     },
                # },
            ],
        }
    ],

    'storage': [
        {
            'enable': True,
        }
    ],
}