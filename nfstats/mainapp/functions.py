import os
from .models import Settings, Host, Interface, Speed
from .settings_sys import SYS_SETTINGS, VARS, logger
from pathlib import Path
import re
import subprocess
from collections import namedtuple


def create_nfdump_filter(interfaces_smpl, direction_key, snmpid_nsmpl = None, direction_key_nsmpl = None, src_as = None, dst_as= None, src_port= None, dst_port = None):
    if interfaces_smpl:
        filter_str = "( "
        for interface in interfaces_smpl:
            filter_str += f"{direction_key} if {interface.snmpid} or "
        filter_str = filter_str[:-3] + ")"
    else:
        logger.error(f"Not found 'sampling' interfaces in the DB. Check at least one interface as 'sampling' in the settings!")
        raise Exception(f"Error: Not found 'sampling' interfaces in the DB. Check at least one interface as 'sampling' in the settings!")
    if snmpid_nsmpl:
        filter_str += f" and {direction_key_nsmpl} if {snmpid_nsmpl}"
    if src_as:
        filter_str += f" and src as {src_as}"
    if dst_as:
        filter_str += f" and dst as {dst_as}"
    if src_port:
        filter_str += f" and src port {src_port}"
    if dst_port:
        filter_str += f" and dst port {dst_port}"
    return filter_str


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
        logger.critical(f"(Shell) Return: {result.stderr} Command: '{command}'")
        raise Exception(f"Error: (Shell) Return: {result.stderr} Command: '{command}'")
    return re.findall(regexp, result.stdout.decode('utf-8'))



def generate_interface_flows_data(filter_direction, report_direction, date, host, snmpid, as_type, snmpid_aggregate = None):
    if snmpid_aggregate:
        Aggregate_interface = namedtuple("Aggregate_interface", "snmpid")
        interfaces = [ Aggregate_interface(snmpid) for snmpid in snmpid_aggregate ]
    else:
        interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    
    flows_file = get_flows_file(host, date)
    direction_key_filter = 'in' if filter_direction == 'input' else 'out' 
    direction_key_report = 'in' if report_direction == 'input' else 'out'
    as_type_key_filter = 'src' if as_type == 'source' else 'dst'
    as_type_key_report = 's' if as_type == 'source' else 'd'
    if filter_direction == report_direction:
        if snmpid_aggregate:
            filter_keys = create_nfdump_filter(interfaces, direction_key_filter)
            command = (f"{VARS['nfdump']} -r {flows_file} -A {as_type_key_filter}as "
                    f"-O bytes -N -q -o 'fmt:%{as_type_key_report}as,%byt' "
                    f"'{filter_keys}'" )
        else:
            filter_keys = f"{direction_key_filter} if {snmpid}"           
            command = (f"{VARS['nfdump']} -r {flows_file} -A {as_type_key_filter}as,{direction_key_report}if "
                    f"-O bytes -N -q -o 'fmt:%{direction_key_report},%{as_type_key_report}as,%byt' "
                    f"'{filter_keys}'" )
    else:
        filter_keys = create_nfdump_filter(interfaces, direction_key_report)    
        command = (f"{VARS['nfdump']} -r {flows_file} -A {as_type_key_filter}as,{direction_key_report}if "
                f"-O bytes -N -q -o 'fmt:%{direction_key_report},%{as_type_key_report}as,%byt' "
                f"'{filter_keys} and {direction_key_filter} if {snmpid}'" )
    if snmpid_aggregate:
        result_aggr = get_shell_data(command, r'\s*(\d+),\s*(\d+)') 
        result = [ (bgp_as,bgp_as,octets) for bgp_as,octets in result_aggr ]
    else:
        result = get_shell_data(command, r'\s*(\d+),\s*(\d+),\s*(\d+)') 
    return result


def generate_interface_flows_sum(direction, date, host):
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flows_file = get_flows_file(host, date)
    direction_key = 'in' if direction == 'input' else 'out'
    filter_keys = create_nfdump_filter(interfaces, direction_key)
    command = ( f"{VARS['nfdump']} -r {flows_file} -A {direction_key}if "
                f"-O bytes -N -q -o 'fmt:%{direction_key},%byt' "
                f"'{filter_keys}'" )
    result = get_shell_data(command, r'\s*(\d+),\s*(\d+)')
    return result


def generate_as_flows_data(direction, date, host):
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flows_file = get_flows_file(host, date)

    direction_key = 'in' if direction == 'input' else 'out'
    filter_keys = create_nfdump_filter(interfaces, direction_key)
    command = ( f"{VARS['nfdump']} -r {flows_file} -A inif,outif,srcas,dstas "
                f"-O bytes -N -q -o 'fmt:%in,%out,%sas,%das,%byt' "
                f"'{filter_keys}'" )
    result = get_shell_data(command, r'\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)')
    return result


def generate_ip_flows_data(direction, date, host, snmpid_smpl, snmpid_nsmpl, src_as, dst_as, src_port, dst_port, ip_type):
    if snmpid_smpl:
        interfaces = Interface.objects.filter(host__host = host, sampling = True, snmpid = int(snmpid_smpl)).all()
    else:
        interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flows_file = get_flows_file(host, date)
    direction_key = 'in' if direction == 'input' else 'out'
    direction_key_nsmpl = 'out' if direction == 'input' else 'in'
    ip_type_key = 'src' if ip_type == 'ip-source-address' else 'dst'
    filter_keys = create_nfdump_filter(interfaces, direction_key, snmpid_nsmpl, direction_key_nsmpl, src_as, dst_as, src_port, dst_port)
    command = (f"{VARS['nfdump']} -r {flows_file} -A {ip_type_key}ip,{direction_key}if "
            f"-O bytes -N -q -o 'fmt:%{ip_type_key[:-2]}a,%{direction_key},%byt' "
            f"'{filter_keys}'")
    result = get_shell_data(command, r'\s*(\d+.\d+.\d+.\d+),\s*(\d+),\s*(\d+)')
    return result


def generate_ip_traffic_data(direction, date, host, snmpid_smpl, snmpid_nsmpl, src_as, dst_as, src_port, dst_port, ip_type, ip_addr):
    if snmpid_smpl:
        interfaces = Interface.objects.filter(host__host = host, sampling = True, snmpid = int(snmpid_smpl)).all()
    else:
        interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flows_file = get_flows_file(host, date)
    
    direction_key = 'in' if direction == 'input' else 'out'
    direction_key_nsmpl = 'out' if direction == 'input' else 'in'
    ip_type_key = 'src' if ip_type == 'ip-source-address' else 'dst'
    filter_keys = create_nfdump_filter(interfaces, direction_key, snmpid_nsmpl, direction_key_nsmpl, src_as, dst_as, src_port, dst_port)
    filter_keys += f" and {ip_type_key} ip {ip_addr}"
    
    command = f"{VARS['nfdump']} -r {flows_file} -N -q -o 'fmt:%ts,%te,%in,%sa,%sp,%out,%da,%dp,%pr,%fl,%pkt,%byt' '{filter_keys}'"
    result = get_shell_data(command, r'\d+\-\d+\-\d+\s+(\d+:\d+:\d+).\d+,\s*\d+\-\d+\-\d+\s+(\d+:\d+:\d+).\d+,\s*(\d+),\s*(\d+.\d+.\d+.\d+),\s*(\d+),\s*(\d+),\s*(\d+.\d+.\d+.\d+),\s*(\d+),\s*(\d+)\s*,\s*(\d+),\s*(\d+),\s*(\d+)')
    return result