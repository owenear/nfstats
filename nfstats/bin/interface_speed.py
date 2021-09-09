import sys, os
from pathlib import Path
import django
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ["DJANGO_SETTINGS_MODULE"] = 'nfstats.settings'
django.setup()
from mainapp.models import Settings, Host, Interface, Speed
from mainapp.settings_sys import SYS_SETTINGS, VARS, logger
import subprocess
import re
import time
from django.utils import timezone
from datetime import datetime, timedelta


def clean_dir(dir_name, oldtime_treshold):
    for file_name in Path(dir_name).glob('**/*'):
        if file_name.is_file() and file_name.stat().st_mtime < oldtime_treshold:
            file_name.unlink()
        if file_name.is_dir():
            try:
                next(file_name.iterdir())
            except StopIteration:
                file_name.rmdir()


def main():
    cur_time = int(time.time())
    
    oldtime_treshold = timezone.now() - timedelta(days=int(SYS_SETTINGS['history_days']))
    Speed.objects.filter(date__lte = oldtime_treshold).delete()
    clean_dir(VARS['flow_filters_dir'], oldtime_treshold.timestamp())
    
    hosts = Host.objects.all()
    for host in hosts:
        clean_dir(host.flow_path, oldtime_treshold.timestamp())
        interfaces = Interface.objects.filter(host = host, sampling = True).all()
        for interface in interfaces:
            snmp_err = 0
            OCTETS_OLD_FILE = Path(VARS['octets_files_dir']).joinpath(host.host + "_" + str(interface.snmpid) + ".old")
            command = f"{VARS['snmp_get']} -v{SYS_SETTINGS['snmp_ver']} -Oseq -c {host.snmp_com} {host.host} .1.3.6.1.2.1.31.1.1.1.6.{interface.snmpid}"
            result = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            if result.stderr:
                logger.error(f"Host: {host}; Interface: {interface}; Return: {result.stderr} Command: '{command}'")
                snmp_err = 1
            else:
                in_octets = re.search(r'.* (\d+)', result.stdout.decode('utf-8')).group(1)    
            command = f"{VARS['snmp_get']} -v{SYS_SETTINGS['snmp_ver']} -Oseq -c {host.snmp_com} {host.host} .1.3.6.1.2.1.31.1.1.1.10.{interface.snmpid}"
            result = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            if result.stderr:
                logger.error(f"Host: {host}; Interface: {interface}; Return: {result.stderr} Command: '{command}'")
                snmp_err = 1
            else:        
                out_octets = re.search(r'.* (\d+)', result.stdout.decode('utf-8')).group(1)
            if snmp_err == 1:
                if OCTETS_OLD_FILE.exists():
                    OCTETS_OLD_FILE.unlink()
                    logger.error(f"Host: {host}; Interface: {interface}; SNMP Error")
                obj = Speed(in_bps = 0, out_bps = 0, date = timezone.make_aware(datetime.fromtimestamp(cur_time).replace(second = 0)), interface = interface)
                obj.save()
            else:
                if not OCTETS_OLD_FILE.exists():
                    obj = Speed(in_bps = 0, out_bps = 0, date = timezone.make_aware(datetime.fromtimestamp(cur_time).replace(second = 0)), interface = interface)
                    obj.save()
                    try:
                        with open(str(OCTETS_OLD_FILE), "w") as file:
                            file.write(f"{cur_time}:{in_octets}:{out_octets}")
                            logger.info(f"Host: {host}; Interface: {interface}; Created Octets File")
                            logger.info(f"Host: {host}; Interface: {interface}; Rec to Octets File")
                    except:
                        logger.error(f"(File R/W): {e}")
                        raise Exception(f"Error: (File R/W): {e}")
                else:
                    try:
                        with open(str(OCTETS_OLD_FILE), "r") as file:
                            speed_data = file.read().split(':')
                    except:
                        logger.error(f"(File R/W): {e}")
                        raise Exception(f"Error: (File R/W): {e}")
                    if len(speed_data) == 3:
                        old_time, old_in_octets, old_out_octets = speed_data
                        if (int(in_octets) >= int(old_in_octets) and int(out_octets) >= int(old_out_octets) and int(cur_time) - int(old_time) < 1000):         
                            in_bps = round((int(in_octets) - int(old_in_octets))*8/(int(cur_time) - int(old_time)), 0)
                            out_bps = round((int(out_octets) - int(old_out_octets))*8/(int(cur_time) - int(old_time)), 0)
                            obj = Speed(in_bps = in_bps, out_bps = out_bps, date = timezone.make_aware(datetime.fromtimestamp(cur_time).replace(second = 0)), interface = interface)
                            obj.save()
                            logger.info(f"Host: {host}; Interface: {interface}; Rec to DB")
                    try:
                        with open(str(OCTETS_OLD_FILE), "w") as file:
                            file.write(f"{cur_time}:{in_octets}:{out_octets}")
                            logger.info(f"Host: {host}; Interface: {interface}; Rec to Octets File")
                    except:
                        logger.error(f"(File R/W): {e}")
                        raise Exception(f"Error: (File R/W): {e}")

if __name__ == "__main__":
    main()