from .models import Settings
import logging
from logging.handlers import WatchedFileHandler
from pathlib import Path
import django.conf 
from django.http import JsonResponse

BASE_DIR = Path(__file__).resolve().parent.parent

SYS_SETTINGS = { 
    'log_file' :  '/var/log/nfstats.log',
    'log_type' : 'console',
    'logging_level' : 'DEBUG',
    'nfdump_bin' : '/usr/bin/',
    'snmp_bin' : '/usr/bin',
    'snmp_ver' : '2c',
    'history_days' : 10,
}

VARS = {}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(levelname)s: %(message)s',
            'datefmt' : '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': [ SYS_SETTINGS['log_type'] ],
            'level': SYS_SETTINGS['logging_level'],
            'propagate': True,
        },
    },
}


def update_globals():
    global SYS_SETTINGS, VARS, BASE_DIR, LOGGING
    
    settings_db = { item['name']:item for item in Settings.objects.values() }
    for name, value in SYS_SETTINGS.items():
        if settings_db.get(name):
            SYS_SETTINGS[name] = settings_db[name]['value']

    VARS.update({
        'data_dir' : BASE_DIR.joinpath('data'),
        'snmp_get' : Path(SYS_SETTINGS['snmp_bin']).joinpath('snmpget'),
        'snmp_walk' : Path(SYS_SETTINGS['snmp_bin']).joinpath('snmpwalk'),
        'nfdump' : Path(SYS_SETTINGS['nfdump_bin']).joinpath('nfdump'),
    })
    Path(VARS['data_dir']).mkdir(parents=True, exist_ok=True)
    LOGGING['loggers']['django']['level'] = SYS_SETTINGS['logging_level']
    django.conf.settings.DEBUG = True if SYS_SETTINGS['logging_level'] == 'DEBUG' else True
    if SYS_SETTINGS['log_type'] == 'file':
        LOGGING['handlers'].update({
            'file': {
                'level': SYS_SETTINGS['logging_level'],
                'class': 'logging.FileHandler',
                'filename':  Path(SYS_SETTINGS['log_file']),
                'formatter' : 'simple'
            },
        })
        LOGGING['loggers']['django'].update({
            'handlers': [SYS_SETTINGS['log_type']],
        })
        try:
            logging.config.dictConfig(LOGGING)
        except ValueError as e:
            LOGGING['handlers'].pop('file')
            LOGGING['loggers']['django']['handlers'] = [ 'console' ]
            raise
    logging.config.dictConfig(LOGGING)


# Update global variables
update_globals()

# Logging configuration
logger = logging.getLogger("django")
