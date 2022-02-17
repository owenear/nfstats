from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Host, Interface, Speed
from .settings_sys import SYS_SETTINGS, VARS, logger
import json
from pathlib import Path
from .functions import generate_ip_flows_data, generate_as_flows_data, generate_interface_flows_sum, generate_interface_flows_data, generate_ip_traffic_data
from .functions import get_shell_data, put_interface_names
import csv
from django.utils import dateparse, timezone
from collections import namedtuple
import re


@csrf_exempt
def get_pie_chart_data(request):
    if request.POST:
        host = request.POST['host'] 
        date_db = dateparse.parse_datetime(request.POST['date'])
        date_format_str = "%Y%m%d%H%M"
        date = timezone.localtime(date_db).strftime(date_format_str)
        direction = request.POST['direction']
        snmpid_aggregate = [] 
        if request.POST['aggregate']:
            snmpid_aggregate = re.findall(r'\d+', request.POST['aggregate'])
            Aggregate_interface = namedtuple("Aggregate_interface", "name description snmpid")
            name_aggregate = ''
            for snmpid in snmpid_aggregate:
                name_aggregate += Interface.objects.get(host__host = host, sampling=True, snmpid = snmpid).name + ', '
            interfaces = [ Aggregate_interface(name=name_aggregate[:-2], description="Aggregate Interface", snmpid = "aggregate") ]
        else:
            interfaces = Interface.objects.filter(host__host = host, sampling = True).all()
        data = {}
        for interface in interfaces:
            snmpid = interface.snmpid
            data[snmpid] = {}
            data[snmpid]['name'] = interface.name
            data[snmpid]['description'] = interface.description
            try:
                if snmpid_aggregate:
                    Aggregate_speed = namedtuple("Aggregate_speed", "in_bps out_bps")
                    speed_data_aggregate = {'in_bps' : 0, 'out_bps' : 0 }
                    for snmpid_part in snmpid_aggregate:
                        speed_data_aggregate['in_bps'] += Speed.objects.get(date = date_db, interface__snmpid = snmpid_part).in_bps
                        speed_data_aggregate['out_bps'] += Speed.objects.get(date = date_db, interface__snmpid = snmpid_part).out_bps
                    speed_data = Aggregate_speed(speed_data_aggregate['in_bps'], speed_data_aggregate['out_bps'])
                else:
                    speed_data = Speed.objects.get(date = date_db, interface = interface)
            except Speed.DoesNotExist:
                logger.error(f"Speed data for the interface {interface} and date: {date_db} does not exist")
                data[snmpid]['error'] = f"Speed data for the interface {interface} and date: {date_db} does not exist"
                continue
            for as_type in ['source', 'destination']:    
                data[snmpid][as_type] = [[as_type + 'AS', 'Mbps']]
                try:
                    flows_data = generate_interface_flows_data(direction, direction, date, host, snmpid, as_type, snmpid_aggregate)
                except Exception as e:
                    data[snmpid]['error'] = str(e)
                    continue
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
    date_db = dateparse.parse_datetime(request.POST['date'])
    date_format_str = "%Y%m%d%H%M"
    date = timezone.localtime(date_db).strftime(date_format_str)
    filter_direction = request.POST['direction']
    snmpid = request.POST['interface']
    report_direction = 'output' if filter_direction == 'input' else 'input'
    data = [[{'label':'Point 1', 'type' : 'string'},{'label':'Point 2', 'type' : 'string'},{'label':'Mbps', 'type' : 'number'}]]
    try:
        flows_sum = generate_interface_flows_sum(report_direction, date, host)
    except Exception as e:
        result = JsonResponse({"error": str(e)})
        result.status_code = 500
        return result
    speed_factor = {}
    for intrf, octets in flows_sum:
        interface = Interface.objects.get(snmpid = int(intrf), host__host = host)
        try:
            speed_data = Speed.objects.get(date = date_db, interface = interface)
        except Speed.DoesNotExist:
            logger.error(f"Speed data for the interface {interface} and date: {date_db} does not exist")
            result = JsonResponse({"error": f"Speed data for the interface {interface} and date: {date_db} does not exist"})
            result.status_code = 500
            return result
        factor = speed_data.in_bps/(int(octets)*1000000) if filter_direction == 'output' else  speed_data.out_bps/(int(octets)*1000000)
        speed_factor[intrf] = factor
    for as_type in [ 'source', 'destination' ]:
        try:
            flows_data = generate_interface_flows_data(filter_direction, report_direction, date, host, snmpid, as_type)
        except Exception as e:
            result = JsonResponse({"error": str(e)})
            result.status_code = 500
            return result
        for intrf, as_bgp,octets in flows_data:
            speed = round(speed_factor[intrf]*int(octets),2)
            intrf = put_interface_names(host, intrf)
            data.append(['sAS' + as_bgp, intrf, speed]) if as_type == 'source' else data.append([intrf, 'dAS' + as_bgp, speed])   
    return HttpResponse(json.dumps(data))


@csrf_exempt
def get_as_chart_data(request):
    if request.POST:
        host = request.POST['host'] 
        date_db = dateparse.parse_datetime(request.POST['date'])
        date_format_str = "%Y%m%d%H%M"
        date = timezone.localtime(date_db).strftime(date_format_str)
        src_as = request.POST['src-as'] 
        dst_as = request.POST['dst-as']
        direction = request.POST['direction']  
        try:
            flows_data = generate_as_flows_data(direction, date, host)
        except Exception as e:
            result = JsonResponse({"error": str(e)})
            result.status_code = 500
            return result
        try:
            flows_sum = generate_interface_flows_sum(direction, date, host)
        except Exception as e:
            result = JsonResponse({"error": str(e)})
            result.status_code = 500
            return result
        speed_factor = {}
        for intrf, octets in flows_sum:
            interface = Interface.objects.get(snmpid = int(intrf), host__host = host)
            try:
                speed_data = Speed.objects.get(date = date_db, interface = interface)
            except Speed.DoesNotExist:
                logger.error(f"Speed data for the interface {interface} and date: {date_db} does not exist")
                result = JsonResponse({"error": f"Speed data for the interface {interface} and date: {date_db} does not exist"})
                result.status_code = 500
                return result
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
    date_db = dateparse.parse_datetime(request.POST['date'])
    date_format_str = "%Y%m%d%H%M"
    date = timezone.localtime(date_db).strftime(date_format_str)
    direction = request.POST['direction']
    src_as = request.POST['src_as'] 
    dst_as = request.POST['dst_as']
    ip_type = request.POST['ip_type']
    src_port = request.POST['src_port'] 
    dst_port = request.POST['dst_port']
    snmpid_smpl = request.POST['interface_sampling']
    snmpid_nsmpl = request.POST['interface']
    count = int(request.POST['count'])
    data = [[{'label':'IP', 'type' : 'string'},{'label':'Mbps', 'type' : 'number'}]]
    data_agr = {}
    try:
        flows_sum = generate_interface_flows_sum(direction, date, host)
    except Exception as e:
        result = JsonResponse({"error": str(e)})
        result.status_code = 500
        return result
    try:
        flows_data = generate_ip_flows_data(direction, date, host, snmpid_smpl, snmpid_nsmpl, src_as, dst_as, src_port, dst_port, ip_type)
    except Exception as e:
        result = JsonResponse({"error": str(e)})
        result.status_code = 500
        return result
    speed_factor = {}
    for intrf, octets in flows_sum:
        interface = Interface.objects.get(snmpid = int(intrf), host__host = host)
        try:
            speed_data = Speed.objects.get(date = date_db, interface = interface)
        except Speed.DoesNotExist:
            logger.error(f"Speed data for the interface {interface} and date: {date_db} does not exist")
            result = JsonResponse({"error": f"Speed data for the interface {interface} and date: {date_db} does not exist"})
            result.status_code = 500
            return result
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
    date_db = dateparse.parse_datetime(request.POST['date'])
    date_format_str = "%Y%m%d%H%M"
    date = timezone.localtime(date_db).strftime(date_format_str)
    ip_addr = request.POST['ip_addr'] 
    direction = request.POST['direction']
    src_as = request.POST['src_as'] 
    dst_as = request.POST['dst_as']
    ip_type = request.POST['ip_type']
    src_port = request.POST['src_port'] 
    dst_port = request.POST['dst_port']
    snmpid_smpl = request.POST['interface_sampling']
    snmpid_nsmpl = request.POST['interface']
    try:
        flows_data = generate_ip_traffic_data(direction, date, host, snmpid_smpl, snmpid_nsmpl, src_as, dst_as, src_port, dst_port, ip_type, ip_addr)
    except Exception as e:
        result = JsonResponse({"error": str(e)})
        result.status_code = 500
        return result

    header = ['Start', 'End', 'Source Interface ID', 'Source IP' , 'Source Port', 
    'Destination Interface ID', 'Destination IP' , 'Destination Port', 
    'Protocols', 'Flows', 'Packets', 'Octets']
    try:
        with open(Path(VARS['data_dir']).joinpath(f"ip_traffic_data_{request.session['session_id']}.csv").resolve(), 'w', encoding='utf8') as f:
            writer = csv.DictWriter(f, fieldnames = header)
            writer.writeheader()
            writer = csv.writer(f)
            writer.writerows(flows_data)
    except Exception as e:
        logger.error(f"(File R/W): {e}")
        result = JsonResponse({"error": f"Error: (File R/W): {e}"})
        result.status_code = 500
        return result
    return HttpResponse(json.dumps(flows_data))


@csrf_exempt
def download_ip_traffic_data(request):
    date_db = dateparse.parse_datetime(request.GET['date'])
    date = timezone.localtime(date_db).strftime("%Y-%m-%d.%H%M")
    ip = request.GET['ip']
    file_path = Path(VARS['data_dir']).joinpath(f"ip_traffic_data_{request.session['session_id']}.csv")
    try:
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type="text/csv")
            response['Content-Disposition'] = 'attachment; filename=' + ip + '_' + date + '.csv'
            return response
    except Exception as e:
        logger.error(f"(File R/W): {e}")
        result = JsonResponse({"error": f"Error: (File R/W): {e}"})
        result.status_code = 500
        return result