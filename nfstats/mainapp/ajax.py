from django.http import HttpResponse
from django.http import JsonResponse
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from .models import Settings, Host, Interface, Speed
from .settings_sys import BASE_DIR, SYS_SETTINGS, set_sys_settings, logger
import json
import os
from pathlib import Path
import re
import subprocess


set_sys_settings()
FLOW_CAT = os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-cat')
FLOW_NFILTER = os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-nfilter')
FLOW_FILTER = os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-filter')
FLOW_REPORT = os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-report')
FLOW_PRINT = os.path.join(SYS_SETTINGS['flowtools_bin'], 'flow-print')
FLOW_FILTERS_DIR =  os.path.join(BASE_DIR, 'flow-tools/')

Path(FLOW_FILTERS_DIR).mkdir(parents=True, exist_ok=True)

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

        
def generate_as_flows_data(direction, date, host):
    report_file = os.path.join(FLOW_FILTERS_DIR, 'report_as.cfg')
    filter_file = os.path.join(FLOW_FILTERS_DIR, 'filter_as.cfg')
    filter_name = 'sum-if-filter'
    report_name = 'as-if-report'
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flow_path = Host.objects.get(host = host).flow_path
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
    try:
        flows_file = next(Path(flow_path).rglob(f'*{date}*'))
    except StopIteration:
        raise Exception(f"Error: Flow files for the date: {date} not found!")
    command = (f"{FLOW_CAT}  {flows_file}* | "
               f"{FLOW_NFILTER} -f {filter_file} -F {filter_name} | "   
               f"{FLOW_REPORT} -s {report_file} -S {report_name} ")
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    result = re.findall(r'(\d+),(\d+),(\d+),(\d+),(\d+)', command_res.stdout.decode('utf-8'))
    return result


def generate_interface_flows_sum(direction, date, host):
    filter_file = os.path.join(FLOW_FILTERS_DIR, 'filter_sum.cfg')
    report_file = os.path.join(FLOW_FILTERS_DIR, 'report_sum.cfg')
    filter_name = 'sum-if-filter'
    report_name = 'sum-if-report'
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flow_path = Host.objects.get(host = host).flow_path
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
    try:
        flows_file = next(Path(flow_path).rglob(f'*{date}*'))
    except StopIteration:
        raise Exception(f"Error: Flow files for the date: {date} not found!")
        
    command = (f"{FLOW_CAT}  {flows_file}* | "
               f"{FLOW_NFILTER} -f {filter_file} -F {filter_name} | "    
               f"{FLOW_REPORT} -s {report_file} -S {report_name}")            
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    result = re.findall(r'(\d+),(\d+)', command_res.stdout.decode('utf-8'))
    return result


def get_interface_speed_factor(direction, date, host):
    flows_sum = generate_interface_flows_sum(direction, date, host)
    speed_factor = {}
    for intrf, octets in flows_sum:
        interface = Interface.objects.get(snmpid = int(intrf), host__host = host)
        try:
            speed_data = Speed.objects.get(date = date_db, interface = interface)
        except Speed.DoesNotExist:
            raise Exception(f"Error: Speed data for interface {interface} and date: {date_db} does not exist")
        factor = speed_data.in_bps/(int(octets)*1000000) if direction == 'input' else  speed_data.out_bps/(int(octets)*1000000)
        speed_factor[intrf] = factor
    return speed_factor


def generate_interface_flows_data(filter_direction, report_direction, date, host, snmpid, as_type):
    report_file = os.path.join(FLOW_FILTERS_DIR, 'report_pie.cfg')
    direction_key = 'i' if filter_direction == 'input' else 'I' 
    report_name = f"{snmpid}-if-report"
    filter_file = os.path.join(FLOW_FILTERS_DIR, 'filter_interface.cfg')
    filter_name = 'sum-if-filter'
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flow_path = Host.objects.get(host = host).flow_path
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
    try:
        flows_file = next(Path(flow_path).rglob(f'*{date}*'))
    except StopIteration:
        raise Exception(f"Error: Flow files for the date: {date} not found!")
    
    command = (f"{FLOW_CAT}  {flows_file}* | " 
               f"{FLOW_NFILTER} -f {filter_file} -F {filter_name} | "
               f"{FLOW_FILTER} -{direction_key} {snmpid} | "
               f"{FLOW_REPORT} -s {report_file} -S {report_name} ")            
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    result = re.findall(r'(\d+),(\d+),(\d+)', command_res.stdout.decode('utf-8'))
    return result
    

def generate_ip_flows_data(direction, date, host, snmpid, src_as, dst_as, src_port, dst_port, ip_type):
    report_file = os.path.join(FLOW_FILTERS_DIR, 'report_ip.cfg')
    report_name = "ip-if-report"  
    
    filter_file = os.path.join(FLOW_FILTERS_DIR, 'filter_ip.cfg')
    filter_name = 'sum-if-filter'
    interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
    flow_path = Host.objects.get(host = host).flow_path
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
       filter_com =  f"{FLOW_FILTER} {filter_keys} | "
    
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
    try:
        flows_file = next(Path(flow_path).rglob(f'*{date}*'))
    except StopIteration:
        raise Exception(f"Error: Flow files for the date: {date} not found!")
    
    command = (f"{FLOW_CAT}  {flows_file}* | " 
               f"{FLOW_NFILTER} -f {filter_file} -F {filter_name} | " 
               f"{filter_com}"
               f"{FLOW_REPORT} -s {report_file} -S {report_name} ")               
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    result = re.findall(r'(\d+.\d+.\d+.\d+),(\d+),(\d+)', command_res.stdout.decode('utf-8'))
    return result



@csrf_exempt
def get_pie_chart_data(request):
    if request.POST:
        host = request.POST['host'] 
        date = date_tranform(request.POST['date'])
        date_db = date_tranform_db(request.POST['date'])
        direction = request.POST['direction'] 
        interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
        data = {}
        for interface in interfaces:
            snmpid = interface.snmpid
            data[snmpid] = {}
            data[snmpid]['name'] = interface.name
            data[snmpid]['description'] = interface.description
            try:
                speed_data = Speed.objects.get(date = date_db, interface = interface)
            except Speed.DoesNotExist:
                data[snmpid]['error'] = f"Error: Speed data for interface {interface} and date: {date_db} does not exist"
                continue
                #raise Exception(f"Error: Speed data for interface {interface} and date: {date_db} does not exist")
            for as_type in ['source', 'destination']:    
                data[snmpid][as_type] = [[as_type + 'AS', 'Mbps']]
                flows_data = generate_interface_flows_data(direction, direction, date, host, snmpid, as_type)
                octets_sum = sum([ int(octets) for _,_,octets in flows_data ])
                for _,as_bgp,octets in flows_data:
                    percent = 100*int(octets)/octets_sum
                    if direction == 'input':
                        speed = round(speed_data.in_bps*(percent/100)/1000000,2)
                    else:
                        speed = round(speed_data.out_bps*(percent/100)/1000000,2)
                    data[snmpid][as_type].append([as_bgp, speed]) 
    return HttpResponse(json.dumps(data))


@csrf_exempt
def get_interface_chart_data(request):
    host = request.POST['host']   
    date = date_tranform(request.POST['date'])
    date_db = date_tranform_db(request.POST['date'])
    filter_direction = request.POST['direction']
    snmpid = request.POST['interface']
    report_direction = 'output' if filter_direction == 'input' else 'input'
    data = [[{'label':'Point 1', 'type' : 'string'},{'label':'Point 2', 'type' : 'string'},{'label':'Mbps', 'type' : 'number'}]]
    
    flows_sum = generate_interface_flows_sum(report_direction, date, host)
    speed_factor = {}
    for intrf, octets in flows_sum:
        interface = Interface.objects.get(snmpid = int(intrf), host__host = host)
        try:
            speed_data = Speed.objects.get(date = date_db, interface = interface)
        except Speed.DoesNotExist:
            raise Exception(f"Error: Speed data for interface {interface} and date: {date_db} does not exist")
        factor = speed_data.in_bps/(int(octets)*1000000) if filter_direction == 'output' else  speed_data.out_bps/(int(octets)*1000000)
        speed_factor[intrf] = factor
    for as_type in [ 'source', 'destination' ]:
        flows_data = generate_interface_flows_data(filter_direction, report_direction, date, host, snmpid, as_type)
        for intrf, as_bgp,octets in flows_data:
            speed = round(speed_factor[intrf]*int(octets),2)
            intrf = put_interface_names(host, intrf)
            data.append(['sAS' + as_bgp, intrf, speed]) if as_type == 'source' else data.append([intrf, 'dAS' + as_bgp, speed])   
    return HttpResponse(json.dumps(data))


@csrf_exempt
def get_as_chart_data(request):
    if request.POST:
        host = request.POST['host'] 
        date = date_tranform(request.POST['date'])
        date_db = date_tranform_db(request.POST['date'])
        src_as = request.POST['src-as'] 
        dst_as = request.POST['dst-as']
        direction = request.POST['direction']  
        flows_data = generate_as_flows_data(direction, date, host)
        flows_sum = generate_interface_flows_sum(direction, date, host)
        speed_factor = {}
        for intrf, octets in flows_sum:
            interface = Interface.objects.get(snmpid = int(intrf), host__host = host)
            try:
                speed_data = Speed.objects.get(date = date_db, interface = interface)
            except Speed.DoesNotExist:
                raise Exception(f"Error: Speed data for interface {interface} and date: {date_db} does not exist")
            factor = speed_data.in_bps/(int(octets)*1000000) if direction == 'input' else  speed_data.out_bps/(int(octets)*1000000)
            speed_factor[intrf] = factor
        data = [[{'label':'Point 1', 'type' : 'string'},{'label':'Point 2', 'type' : 'string'},{'label':'Mbps', 'type' : 'number'}]]
        data_agr = {}
        for in_intrf, out_intrf, sas, das, octets in flows_data:
            speed = round(speed_factor[in_intrf]*int(octets),2) if direction == 'input' else round(speed_factor[out_intrf]*int(octets),2)
            if (not src_as or src_as == sas) and (not dst_as or dst_as == das):
                in_intrf = put_interface_names(host, in_intrf)
                out_intrf = put_interface_names(host, out_intrf)
                data_agr.setdefault('sAS ' + sas, {})
                data_agr.setdefault('In ' + in_intrf, {})
                data_agr.setdefault('Out ' + out_intrf, {})
                
                data_agr['sAS ' + sas].setdefault('In ' + in_intrf, 0)
                data_agr['In ' + in_intrf].setdefault('Out ' + out_intrf, 0)             
                data_agr['Out ' + out_intrf].setdefault('dAS ' + das, 0)
                
                data_agr['sAS ' + sas]['In ' + in_intrf] += speed
                data_agr['In ' + in_intrf]['Out ' + out_intrf] += speed
                data_agr['Out ' + out_intrf]['dAS ' + das] += speed
        for point_1, point_dict in data_agr.items():
            for point_2, value in point_dict.items():
                data.append([point_1, point_2, round(value, 2)]) 
    return HttpResponse(json.dumps(data))    


@csrf_exempt
def get_ip_chart_data(request):
    host = request.POST['host']   
    date = date_tranform(request.POST['date'])
    date_db = date_tranform_db(request.POST['date'])
    direction = request.POST['direction']
    src_as = request.POST['src_as'] 
    dst_as = request.POST['dst_as']
    ip_type = request.POST['ip_type']
    src_port = request.POST['src_port'] 
    dst_port = request.POST['dst_port']
    snmpid = request.POST['interface'] 
    count = int(request.POST['count'])
    data = [[{'label':'IP', 'type' : 'string'},{'label':'Mbps', 'type' : 'number'}]]
    data_agr = {}
    flows_sum = generate_interface_flows_sum(direction, date, host)
    flows_data = generate_ip_flows_data(direction, date, host, snmpid, src_as, dst_as, src_port, dst_port, ip_type)
    speed_factor = {}
    for intrf, octets in flows_sum:
        interface = Interface.objects.get(snmpid = int(intrf), host__host = host)
        try:
            speed_data = Speed.objects.get(date = date_db, interface = interface)
        except Speed.DoesNotExist:
            raise Exception(f"Error: Speed data for interface {interface} and date: {date_db} does not exist")
        factor = speed_data.in_bps/(int(octets)*1000000) if direction == 'input' else  speed_data.out_bps/(int(octets)*1000000)
        speed_factor[intrf] = factor
    for address, intrf, octets in flows_data:
        speed = round(speed_factor[intrf]*int(octets),2)
        data_agr.setdefault(address, 0)
        data_agr[address] += speed
    data_agr_list = list(data_agr.items())
    data_agr_list.sort(key=lambda i: i[1], reverse = True)
    for point, value in data_agr_list[:count]:
        data.append([point, round(value, 2)]) 
    return HttpResponse(json.dumps(data))


@csrf_exempt
def get_ip_traffic_data(request):
    host = request.POST['host']   
    date = date_tranform(request.POST['date'])
    date_db = date_tranform_db(request.POST['date'])
    ip_type = request.POST['ip_type']
    ip_addr = request.POST['ip_addr'] 
    filter_file = os.path.join(FLOW_FILTERS_DIR, 'filter_ip_traffic.cfg')
    filter_name = 'ip-filter'
    flow_path = Host.objects.get(host = host).flow_path
    with open(filter_file, 'w', encoding='utf8') as f:
        filter = f'''filter-primitive {filter_name}
  type ip-address
  permit {ip_addr}
filter-definition {filter_name}
  match {ip_type} {filter_name}
'''
        f.write(filter)
    
    try:
        flows_file = next(Path(flow_path).rglob(f'*{date}*'))
    except StopIteration:
        raise Exception(f"Error: Flow files for the date: {date} not found!")
    
    command = (f"{FLOW_CAT}  {flows_file}* | " 
               f"{FLOW_NFILTER} -f {filter_file} -F {filter_name} | "
               f"{FLOW_PRINT} -f5")               
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    result = re.findall(r'\d+.(\d+:\d+:\d+).\d+\s\d+.(\d+:\d+:\d+).\d+\s+(\d+)\s+(\d+.\d+.\d+.\d+)\s+(\d+)\s+(\d+)\s+(\d+.\d+.\d+.\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', command_res.stdout.decode('utf-8'))
    return HttpResponse(json.dumps(result))   