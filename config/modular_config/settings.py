import os
import sys
import importlib

# Add the current directory to sys.path to allow relative imports
config_dir = os.path.dirname(__file__)
if config_dir not in sys.path:
    sys.path.append(config_dir)

# Import modular components
from rfm_logging import logging
from rfm_general import general

# Systems Discovery
systems = []
systems_dir = os.path.join(config_dir, 'systems')
for filename in os.listdir(systems_dir):
    if filename.endswith('.py') and not filename.startswith('__'):
        module_name = f"systems.{filename[:-3]}"
        module = importlib.import_module(module_name)
        # Look for dictionary objects that look like system definitions
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, dict) and 'name' in attr and 'partitions' in attr:
                systems.append(attr)

# Environments Discovery
environments = []
env_dir = os.path.join(config_dir, 'environments')
for filename in os.listdir(env_dir):
    if filename.endswith('.py') and not filename.startswith('__'):
        module_name = f"environments.{filename[:-3]}"
        module = importlib.import_module(module_name)
        # Look for 'environments' list in the module
        if hasattr(module, 'environments'):
            environments.extend(module.environments)

# Final site configuration
site_configuration = {
    'systems': systems,
    'environments': environments,
    'logging': logging,
    'general': general,
    'storage': [
        {
            'enable': True
        }
    ]
}
