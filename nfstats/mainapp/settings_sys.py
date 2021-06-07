from .models import Settings

settings_db = { item['name']:item for item in Settings.objects.values() }

SYS_SETTINGS = { 
    'log_dir' :  '/var/log',
    'log_size' : 50000,
    'flowtools_bin' : '/usr/local/flow-tools/bin',
    'snmp_bin' : '/usr/bin',
    'snmp_com' : 'public',
    'snmp_ver' : '2c',
}


for name, value in SYS_SETTINGS.items():
    if settings_db.get(name):
        SYS_SETTINGS[name] = settings_db[name]['value']

