from .models import Settings
import os, logging
from logging.handlers import WatchedFileHandler


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYS_SETTINGS = { 
    'log_dir' :  '/var/log',
    'log_size' : 50000,
    'flowtools_bin' : '/usr/local/flow-tools/bin',
    'snmp_bin' : '/usr/bin',
    'snmp_com' : 'public',
    'snmp_ver' : '2c',
}


def set_sys_settings():
    '''Getting settings from db'''
    settings_db = { item['name']:item for item in Settings.objects.values() }
    for name, value in SYS_SETTINGS.items():
        if settings_db.get(name):
            SYS_SETTINGS[name] = settings_db[name]['value']


# Logging configuration
LOG_FILE = os.path.join(SYS_SETTINGS['log_dir'], 'nfstats.log')
logger = logging.getLogger("mainlog")
logger.setLevel(logging.INFO)
file_handler = WatchedFileHandler(LOG_FILE)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)