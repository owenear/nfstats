import os
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



def generate_interface_flows_data(session_id, filter_direction, report_direction, date, host, snmpid, as_type):
    report_file = os.path.join(VARS['flow_filters_dir'], f'report_pie_{session_id}.cfg')
    direction_key = 'i' if filter_direction == 'input' else 'I' 
    report_name = f"{snmpid}-if-report"
    filter_file = os.path.join(VARS['flow_filters_dir'], f'filter_interface_{session_id}.cfg')
    filter_name = 'sum-if-filter'
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    create_flow_filter(report_direction, interfaces, filter_file, filter_name) 
    with open(report_file, 'w', encoding='utf8') as f: 
        report = f'''stat-report {report_name}
  type {report_direction}-interface/{as_type}-as
  output
  format ascii
  options -header,-xheader,-totals,-names
  fields -flows,+octets,-packets,-duration
  sort +octets
  
stat-definition {report_name}
  report {report_name}
'''
        f.write(report)        
    flows_file = get_flows_file(host, date)
    command = (f"{VARS['flow_cat']}  {flows_file}* | " 
            f"{VARS['flow_nfilter']} -f {filter_file} -F {filter_name} | "
            f"{VARS['flow_filter']} -{direction_key} {snmpid} | "
            f"{VARS['flow_report']} -s {report_file} -S {report_name} ") 
    result = get_shell_data(command, r'(\d+),(\d+),(\d+)')
    return result


def generate_interface_flows_sum(session_id, direction, date, host):
    filter_file = os.path.join(VARS['flow_filters_dir'], f'filter_sum_{session_id}.cfg')
    report_file = os.path.join(VARS['flow_filters_dir'], f'report_sum_{session_id}.cfg')
    filter_name = 'sum-if-filter'
    report_name = 'sum-if-report'
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    create_flow_filter(direction, interfaces, filter_file, filter_name)
    with open(report_file, 'w', encoding='utf8') as f: 
        report = f'''stat-report {report_name}
  type {direction}-interface
  output
  format ascii
  options -header,-xheader,-totals,-names
  fields -flows,+octets,-packets,-duration
  sort +octets
  
stat-definition {report_name}
  report {report_name}
'''
        f.write(report)        
    flows_file = get_flows_file(host, date)
    command = (f"{VARS['flow_cat']}  {flows_file}* | "
               f"{VARS['flow_nfilter']} -f {filter_file} -F {filter_name} | "    
               f"{VARS['flow_report']} -s {report_file} -S {report_name}")            
    result = get_shell_data(command, r'(\d+),(\d+)')
    return result


def generate_as_flows_data(session_id, direction, date, host):
    report_file = os.path.join(VARS['flow_filters_dir'], f'report_as_{session_id}.cfg')
    filter_file = os.path.join(VARS['flow_filters_dir'], f'filter_as_{session_id}.cfg')
    filter_name = 'sum-if-filter'
    report_name = 'as-if-report'
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    create_flow_filter(direction, interfaces, filter_file, filter_name)
    
    with open(report_file, 'w', encoding='utf8') as f: 
        report = f'''stat-report {report_name}
  type input/output-interface/source/destination-as
  output
  format ascii
  options -header,-xheader,-totals,-names
  fields -flows,+octets,-packets,-duration
  sort +octets
  
stat-definition {report_name}
  report {report_name}
'''
        f.write(report)
        
    flows_file = get_flows_file(host, date)
    command = (f"{VARS['flow_cat']}  {flows_file}* | "
               f"{VARS['flow_nfilter']} -f {filter_file} -F {filter_name} | "   
               f"{VARS['flow_report']} -s {report_file} -S {report_name} ")
    result = get_shell_data(command, r'(\d+),(\d+),(\d+),(\d+),(\d+)')
    return result


def generate_ip_flows_data(session_id, direction, date, host, snmpid, src_as, dst_as, src_port, dst_port, ip_type):
    report_file = os.path.join(VARS['flow_filters_dir'], f'report_ip_{session_id}.cfg')
    report_name = "ip-if-report"  
    
    filter_file = os.path.join(VARS['flow_filters_dir'], f'filter_ip_{session_id}.cfg')
    filter_name = 'sum-if-filter'
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    create_flow_filter(direction, interfaces, filter_file, filter_name)   
    filter_com = ""
    filter_keys = ""
    if snmpid:
        direction_key = 'i' if direction == 'output' else 'I'
        filter_keys += f" -{direction_key} {snmpid}"
    if src_as:
        filter_keys += f" -a {src_as}"
    if dst_as:
        filter_keys += f" -A {dst_as}"
    if src_port:
        filter_keys += f" -p {src_port}"
    if dst_port:
        filter_keys += f" -P {dst_port}"
    if filter_keys:
       filter_com =  f"{VARS['flow_filter']} {filter_keys} | "
    
    with open(report_file, 'w', encoding='utf8') as f: 
        report = f'''stat-report {report_name}
  type {ip_type}/{direction}-interface
  output
  format ascii
  options -header,-xheader,-totals,-names
  fields -flows,+octets,-packets,-duration
  sort +octets
  
stat-definition {report_name}
  report {report_name}
'''
        f.write(report)        

    flows_file = get_flows_file(host, date)
    command = (f"{VARS['flow_cat']}  {flows_file}* | " 
               f"{VARS['flow_nfilter']} -f {filter_file} -F {filter_name} | " 
               f"{filter_com}"
               f"{VARS['flow_report']} -s {report_file} -S {report_name} ")
    result = get_shell_data(command, r'(\d+.\d+.\d+.\d+),(\d+),(\d+)')
    return result