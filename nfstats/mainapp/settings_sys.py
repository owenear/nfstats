from .models import Settings
import logging
from logging.handlers import WatchedFileHandler
from pathlib import Path
import django.conf 
from django.http import JsonResponse

BASE_DIR = Path(__file__).resolve().parent.parent

SYS_SETTINGS = { 
    'log_file' :  '/var/log/nfstats.log',
    'log_type' : 'file',
    'flow_collector' : 'flow-tools',
    'logging_level' : 'DEBUG',
    'log_size' : 50000,
    'flow_collector_bin' : '/usr/local/bin/',
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
        'file': {
            'level': SYS_SETTINGS['logging_level'],
            'class': 'logging.FileHandler',
            'filename':  Path(SYS_SETTINGS['log_file']),
            'formatter' : 'simple'
        },
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


def set_vars():
    global VARS, BASE_DIR
    VARS.update({
        'octets_files_dir' : BASE_DIR.joinpath('speed'),
        'flow_filters_dir' : BASE_DIR.joinpath('flow-tools'),
        'snmp_get' : Path(SYS_SETTINGS['snmp_bin']).joinpath('snmpget'),
        'snmp_walk' : Path(SYS_SETTINGS['snmp_bin']).joinpath('snmpwalk'),
        'flow_cat' : Path(SYS_SETTINGS['flow_collector_bin']).joinpath('flow-cat'),
        'flow_nfilter' : Path(SYS_SETTINGS['flow_collector_bin']).joinpath('flow-nfilter'),
        'flow_filter' : Path(SYS_SETTINGS['flow_collector_bin']).joinpath('flow-filter'),
        'flow_report' : Path(SYS_SETTINGS['flow_collector_bin']).joinpath('flow-report'),
        'flow_print' : Path(SYS_SETTINGS['flow_collector_bin']).joinpath('flow-print'),
        'nfdump' : Path(SYS_SETTINGS['flow_collector_bin']).joinpath('nfdump'),
    })
    Path(VARS['octets_files_dir']).mkdir(parents=True, exist_ok=True)
    Path(VARS['flow_filters_dir']).mkdir(parents=True, exist_ok=True)
    '''
    if not Path(SYS_SETTINGS['log_file']).exists():
        try:
            Path(SYS_SETTINGS['log_file']).touch()
        except Exception as e:
            result = JsonResponse({"error": f"Error: (DB): {e}"})
            result.status_code = 500
            return result
    if Path(SYS_SETTINGS['log_file']).exists():
        LOGGING['handlers'].update({
            'file': {
                'level': SYS_SETTINGS['logging_level'],
                'class': 'logging.FileHandler',
                'filename':  SYS_SETTINGS['log_file'],
                'formatter' : 'simple'
            },
        })
        #LOGGING['handlers']['file']['filename'] = SYS_SETTINGS['log_file']
        #LOGGING['handlers']['file']['level'] = SYS_SETTINGS['logging_level']
        LOGGING['loggers']['django']['handlers'] = 'file'
    '''
    LOGGING['handlers']['file']['filename'] = SYS_SETTINGS['log_file']
    LOGGING['handlers']['file']['level'] = SYS_SETTINGS['logging_level']
    LOGGING['loggers']['django']['level'] = SYS_SETTINGS['logging_level']
    django.conf.settings.DEBUG = True if SYS_SETTINGS['logging_level'] == 'DEBUG' else True


def update_sys_settings():
    global SYS_SETTINGS
    settings_db = { item['name']:item for item in Settings.objects.values() }
    for name, value in SYS_SETTINGS.items():
        if settings_db.get(name):
            SYS_SETTINGS[name] = settings_db[name]['value']


def update_globals():
    update_sys_settings()
    set_vars()
    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger("django")


# Update global variables
update_globals()

# Logging configuration
logger = logging.getLogger("django")