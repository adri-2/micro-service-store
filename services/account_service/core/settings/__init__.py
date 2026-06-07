"""
Settings module initialization
Automatically loads the appropriate settings based on DJANGO_SETTINGS_MODULE environment variable
"""

import os
from decouple import config
# Get the environment from DJANGO_ENV or default to 'dev'
environment = config('DJANGO_ENV', default='dev')

# Import the appropriate settings
if environment == 'prod':
    from .prod import *
elif environment == 'dev':
    from .dev import *
else:
    from .dev import *
