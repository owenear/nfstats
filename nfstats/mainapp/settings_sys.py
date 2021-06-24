from .models import Settings
import os, logging
from logging.handlers import WatchedFileHandler
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYS_SETTINGS = { 
    'log_dir' :  '/var/log',
    'log_size' : 50000,
    'flowtools_bin' : '/usr/local/flow-tools/bin',
    'snmp_bin' : '/usr/bin',
    'snmp_com' : 'public',
    'snmp_ver' : '2c',
    'history_days' : 5,
}

VARS = { }

def set_vars():
    global VARS, BASE_DIR
    VARS.update({
        'octets_files_dir' : os.path.join(BASE_DIR, 'speed'),
        'flow_filters_dir' : os.path.join(BASE_DIR, 'flow-tools/'),
        'log_file' : os.path.join(SYS_SETTINGS['log_dir'], 'nfstats.log'),
        'snmp_get' : os.path.join(SYS_SETTINGS['snmp_bin'], 'snmpget'),
        'snmp_walk' : os.path.join(SYS_SETTINGS['snmp_bin'], 'snmpwalk'),
        'flow_cat' : os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-cat'),
        'flow_nfilter' : os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-nfilter'),
        'flow_filter' : os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-filter'),
        'flow_report' : os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-report'),
        'flow_print' : os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-print'),
    })
    Path(VARS['octets_files_dir']).mkdir(parents=True, exist_ok=True)
    Path(VARS['flow_filters_dir']).mkdir(parents=True, exist_ok=True)


def update_sys_settings():
    global SYS_SETTINGS
    settings_db = { item['name']:item for item in Settings.objects.values() }
    for name, value in SYS_SETTINGS.items():
        if settings_db.get(name):
            SYS_SETTINGS[name] = settings_db[name]['value']


def update_globals():
    update_sys_settings()
    set_vars()


# Update global variables
update_globals()

# Logging configuration
logger = logging.getLogger("mainlog")
logger.setLevel(logging.INFO)
file_handler = WatchedFileHandler(VARS['log_file'])
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)