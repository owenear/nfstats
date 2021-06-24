from .models import Settings, Host, Interface, Speed
from .settings_sys import SYS_SETTINGS, VARS, logger
from pathlib import Path
import re
import subprocess


def date_tranform(date):
    date_re = re.match(r'(\d+).(\d+).(\d+)\s(\d+):(\d+)', date)
    return f"{date_re.group(3)}-{date_re.group(2)}-{date_re.group(1)}.{date_re.group(4)}{date_re.group(5)}"

    
def date_tranform_db(date):
    date_re = re.match(r'(\d+).(\d+).(\d+)\s(\d+):(\d+)', date)
    return f"{date_re.group(3)}-{date_re.group(2)}-{date_re.group(1)} {date_re.group(4)}:{date_re.group(5)}"


def create_flow_filter(direction, interfaces, filter_file, filter_name):
    filter_str = f'''filter-primitive {filter_name}
  type ifindex
'''
    for interface in interfaces:
        filter_str += f"  permit {interface.snmpid}\n"
    with open(filter_file, 'w', encoding='utf8') as f: 
        filter = f'''{filter_str}
filter-definition {filter_name}
  match {direction}-interface {filter_name}
'''
        f.write(filter)


def put_interface_names(host, snmpid):
    interface = Interface.objects.filter(host__host = host, snmpid = int(snmpid)).first()
    if interface:
        return interface.description
    else:
        return snmpid


def get_flows_file(host, date):
    flow_path = Host.objects.get(host = host).flow_path
    try:
        result = next(Path(flow_path).rglob(f'*{date}*'))
    except StopIteration:
        logger.error(f"Flow files for the date: {date} not found!")
        raise Exception(f"Error: Flow files for the date: {date} not found!")
    return result


def get_shell_data(command, regexp):
    result = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if result.stderr:
        logger.error(f"(SH) Return: {result.stderr} Command: '{command}'")
        raise Exception(f"Error: (SH) Return: {result.stderr} Command: '{command}'")
    return re.findall(regexp, result.stdout.decode('utf-8'))



