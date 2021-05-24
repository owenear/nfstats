import sys, os
import django
import logging.handlers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DJANGO_SETTINGS_MODULE"] = 'nfstats.settings'
django.setup()
from mainapp.models import *
from configparser import ConfigParser
import subprocess
import re
import time
from datetime import datetime, timedelta
from pathlib import Path


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config = ConfigParser(allow_no_value=True)
config.read(os.path.join(BASE_DIR, 'config.ini'))

OCTETS_OLD_FILE_PREFIX = os.path.join(BASE_DIR, 'speed')
Path(OCTETS_OLD_FILE_PREFIX).mkdir(parents=True, exist_ok=True)

LOG_FILE = os.path.join(config['SYSTEM']['LogDir'], 'nfstat-interface-speed.log')
LOG_FILE_SIZE = int(config['SYSTEM']['LogFileSize'])

SNMP_COM = config['SNMP']['Community']
SNMP_VER = config['SNMP']['Version']
SNMP_GET = os.path.join(config['FILES']['SnmpToolsBinDir'], 'snmpget')

Speed.objects.filter(date__lte = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M')).delete()
hosts = Host.objects.all()

# Logging configuration
logger = logging.getLogger("mainlog")
logger.setLevel(logging.INFO)
fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=LOG_FILE_SIZE, backupCount=5)
fh.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger.addHandler(fh)

def log(msg = '', level = 6):
    if os.path.getsize(LOG_FILE) == 0:
        logger.info("LogFile created")
    if level == 3:
        logger.error(f"ERROR: {msg}")
    else:
        logger.info(f"{msg}")

cur_time = int(time.time())


for host in hosts:
    interfaces = Interface.objects.filter(host = host, sampling = True).all()
    for interface in interfaces:
        snmp_err = 0
        OCTETS_OLD_FILE = os.path.join(OCTETS_OLD_FILE_PREFIX, host.host + "_" + str(interface.snmpid) + ".old")
        command = f"{SNMP_GET} -v{SNMP_VER} -Oseq -c {SNMP_COM} {host.host} .1.3.6.1.2.1.31.1.1.1.6.{interface.snmpid}"
        result = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        if result.stderr:
            log(f"Host: {host}; Interface: {interface}; Return: {result.stderr} Command: '{command}'", level=3)
            snmp_err = 1
        else:
            in_octets = re.search(r'.* (\d+)', result.stdout.decode('utf-8')).group(1)    
        command = f"{SNMP_GET} -v{SNMP_VER} -Oseq -c {SNMP_COM} {host.host} .1.3.6.1.2.1.31.1.1.1.10.{interface.snmpid}"
        result = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        if result.stderr:
            log(f"Host: {host}; Interface: {interface}; Return: {result.stderr} Command: '{command}'", level=3)
            snmp_err = 1
        else:        
            out_octets = re.search(r'.* (\d+)', result.stdout.decode('utf-8')).group(1)
        if snmp_err == 1:
            if os.path.exists(OCTETS_OLD_FILE):
                os.remove(OCTETS_OLD_FILE)
                log(f"Host: {host}; Interface: {interface}; SNMP Error", level=3)
            obj = Speed(in_bps = 0, out_bps = 0, date = datetime.fromtimestamp(cur_time).strftime('%Y-%m-%d %H:%M'), interface = interface)
            obj.save()
        else:
            if not os.path.exists(OCTETS_OLD_FILE):
                obj = Speed(in_bps = 0, out_bps = 0, date = datetime.fromtimestamp(cur_time).strftime('%Y-%m-%d %H:%M'), interface = interface)
                obj.save()
                with open(OCTETS_OLD_FILE, "w") as file:
                    file.write(f"{cur_time}:{in_octets}:{out_octets}")
                    log(f"Host: {host}; Interface: {interface}; Created Octets File")
                    log(f"Host: {host}; Interface: {interface}; Rec to Octets File")
            else:
                with open(OCTETS_OLD_FILE, "r") as file:
                    speed_data = file.read().split(':')
                if len(speed_data) == 3:
                    old_time, old_in_octets, old_out_octets = speed_data
                    if (int(in_octets) >= int(old_in_octets) and int(out_octets) >= int(old_out_octets) and int(cur_time) - int(old_time) < 1000):         
                        in_bps = round((int(in_octets) - int(old_in_octets))*8/(int(cur_time) - int(old_time)), 0)
                        out_bps = round((int(out_octets) - int(old_out_octets))*8/(int(cur_time) - int(old_time)), 0)
                        obj = Speed(in_bps = in_bps, out_bps = out_bps, date = datetime.fromtimestamp(cur_time).strftime('%Y-%m-%d %H:%M'), interface = interface)
                        obj.save()
                        log(f"Host: {host}; Interface: {interface}; Rec to DB")
                with open(OCTETS_OLD_FILE, "w") as file:
                    file.write(f"{cur_time}:{in_octets}:{out_octets}")
                    log(f"Host: {host}; Interface: {interface}; Rec to Octets File")
                        