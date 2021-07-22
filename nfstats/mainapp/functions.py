import os
from .models import Settings, Host, Interface, Speed
from .settings_sys import SYS_SETTINGS, VARS, logger
from pathlib import Path
import re
import subprocess


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


def create_nfdump_filter(direction, interfaces):
    filter_str = "( "
    for interface in interfaces:
        filter_str += f"{direction} if {interface.snmpid} or "
    return filter_str[:-3] + ")"


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
        logger.critical(f"(SH) Return: {result.stderr} Command: '{command}'")
        raise Exception(f"Error: (SH) Return: {result.stderr} Command: '{command}'")
    return re.findall(regexp, result.stdout.decode('utf-8'))



def generate_interface_flows_data(session_id, filter_direction, report_direction, date, host, snmpid, as_type):
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flows_file = get_flows_file(host, date)

    if SYS_SETTINGS['flow_collector'] == 'flow-tools':
        report_file = os.path.join(VARS['flow_filters_dir'], f'report_pie_{session_id}.cfg')
        direction_key = 'i' if filter_direction == 'input' else 'I' 
        report_name = f"{snmpid}-if-report"      
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
        
        if filter_direction == report_direction:
            command = (f"{VARS['flow_cat']}  {flows_file}* | " 
                    f"{VARS['flow_filter']} -{direction_key} {snmpid} | "
                    f"{VARS['flow_report']} -s {report_file} -S {report_name} ")
        else:
            filter_file = os.path.join(VARS['flow_filters_dir'], f'filter_interface_{session_id}.cfg')
            filter_name = 'sum-if-filter'
            create_flow_filter(report_direction, interfaces, filter_file, filter_name)
            command = (f"{VARS['flow_cat']}  {flows_file}* | " 
                f"{VARS['flow_nfilter']} -f {filter_file} -F {filter_name} | "
                f"{VARS['flow_filter']} -{direction_key} {snmpid} | "
                f"{VARS['flow_report']} -s {report_file} -S {report_name} ")
    else:
        direction_key_filter = 'in' if filter_direction == 'input' else 'out' 
        direction_key_report = 'in' if report_direction == 'input' else 'out'
        as_type_key_filter = 'src' if as_type == 'source' else 'dst'
        as_type_key_report = 's' if as_type == 'source' else 'd'
        if filter_direction == report_direction:
            command = (f"{VARS['nfdump']} -r {flows_file} -A {as_type_key_filter}as,{direction_key_report}if "
                    f"-O bytes -N -q -o 'fmt:%{direction_key_report},%{as_type_key_report}as,%byt' "
                    f"'{direction_key_filter} if {snmpid}'"
            )
        else:
            filter_keys = create_nfdump_filter(direction_key_report, interfaces)    
            command = (f"{VARS['nfdump']} -r {flows_file} -A {as_type_key_filter}as,{direction_key_report}if "
                    f"-O bytes -N -q -o 'fmt:%{direction_key_report},%{as_type_key_report}as,%byt' "
                    f"'{filter_keys} and {direction_key_filter} if {snmpid}'"
            )
    result = get_shell_data(command, r'\s*(\d+),\s*(\d+),\s*(\d+)')
    return result


def generate_interface_flows_sum(session_id, direction, date, host):
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flows_file = get_flows_file(host, date)
    if SYS_SETTINGS['flow_collector'] == 'flow-tools':
        filter_file = os.path.join(VARS['flow_filters_dir'], f'filter_sum_{session_id}.cfg')
        report_file = os.path.join(VARS['flow_filters_dir'], f'report_sum_{session_id}.cfg')
        filter_name = 'sum-if-filter'
        report_name = 'sum-if-report'
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
        command = (f"{VARS['flow_cat']}  {flows_file}* | "
                f"{VARS['flow_nfilter']} -f {filter_file} -F {filter_name} | "    
                f"{VARS['flow_report']} -s {report_file} -S {report_name}")
    else:
        direction_key = 'in' if direction == 'input' else 'out'
        filter_keys = create_nfdump_filter(direction_key, interfaces)
        command = (f"{VARS['nfdump']} -r {flows_file} -A {direction_key}if "
        f"-O bytes -N -q -o 'fmt:%{direction_key},%byt' "
        f"'{filter_keys}'"
        )
    result = get_shell_data(command, r'\s*(\d+),\s*(\d+)')
    return result


def generate_as_flows_data(session_id, direction, date, host):
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flows_file = get_flows_file(host, date)
    if SYS_SETTINGS['flow_collector'] == 'flow-tools':
        report_file = os.path.join(VARS['flow_filters_dir'], f'report_as_{session_id}.cfg')
        filter_file = os.path.join(VARS['flow_filters_dir'], f'filter_as_{session_id}.cfg')
        filter_name = 'sum-if-filter'
        report_name = 'as-if-report'
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
        command = (f"{VARS['flow_cat']}  {flows_file}* | "
                f"{VARS['flow_nfilter']} -f {filter_file} -F {filter_name} | "   
                f"{VARS['flow_report']} -s {report_file} -S {report_name} ")
    else:
        direction_key = 'in' if direction == 'input' else 'out'
        filter_keys = create_nfdump_filter(direction_key, interfaces)
        command = (f"{VARS['nfdump']} -r {flows_file} -A inif,outif,srcas,dstas "
        f"-O bytes -N -q -o 'fmt:%in,%out,%sas,%das,%byt' "
        f"'{filter_keys}'"
        )
    result = get_shell_data(command, r'\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)')
    return result


def generate_ip_flows_data(session_id, direction, date, host, snmpid, src_as, dst_as, src_port, dst_port, ip_type):
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flows_file = get_flows_file(host, date)

    if SYS_SETTINGS['flow_collector'] == 'flow-tools':
        report_file = os.path.join(VARS['flow_filters_dir'], f'report_ip_{session_id}.cfg')
        report_name = "ip-if-report"  
        filter_file = os.path.join(VARS['flow_filters_dir'], f'filter_ip_{session_id}.cfg')
        filter_name = 'sum-if-filter'
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

        command = (f"{VARS['flow_cat']}  {flows_file}* | " 
                f"{VARS['flow_nfilter']} -f {filter_file} -F {filter_name} | " 
                f"{filter_com}"
                f"{VARS['flow_report']} -s {report_file} -S {report_name} ")
    else:
        direction_key = 'in' if direction == 'input' else 'out'
        ip_type_key_filter = 'src' if ip_type == 'source' else 'dst'
        ip_type_key_report = 's' if ip_type == 'source' else 'd'
        if snmpid:
            filter_keys = f"{direction_key} if {snmpid}"
        else:
            filter_keys = create_nfdump_filter(direction_key, interfaces)
        if src_as:
            filter_keys += f" and src as {src_as}"
        if dst_as:
            filter_keys += f" and dst as {dst_as}"
        if src_port:
            filter_keys += f" and src port {src_port}"
        if dst_port:
            filter_keys += f" and dst port {dst_port}"
        command = (f"{VARS['nfdump']} -r {flows_file} -A {ip_type_key_filter}ip,{direction_key}if "
                f"-O bytes -N -q -o 'fmt:%{ip_type_key_report}a,%{direction_key},%byt' "
                f"'{filter_keys}'")
    result = get_shell_data(command, r'\s*(\d+.\d+.\d+.\d+),\s*(\d+),\s*(\d+)')
    return result