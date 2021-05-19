from django.http import HttpResponse
from django.http import JsonResponse
from django.core import serializers
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from .models import *
import json

import os
from configparser import ConfigParser
from pathlib import Path
import re
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config = ConfigParser(allow_no_value=True)
config.read(os.path.join(BASE_DIR, 'config.ini'))

SNMP_COM = config['SNMP']['Community']
SNMP_VER = config['SNMP']['Version']
SNMP_WALK = os.path.join(config['FILES']['SnmpToolsBinDir'], 'snmpwalk')

@csrf_exempt
def get_snmp_interfaces(request):
    host = request.POST['host']

    command = f"{SNMP_WALK} -v{SNMP_VER} -Oseq -c {SNMP_COM} {host} interfaces.ifTable.ifEntry.ifDescr"
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if_names = re.findall(r'\w+.(\d+)\s(.*)', command_res.stdout.decode('utf-8'))
    command = f"{SNMP_WALK} -v{SNMP_VER} -Oseq -c {SNMP_COM} {host} ifMIB.ifMIBObjects.ifXTable.ifXEntry.ifAlias"
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if_descriptions = re.findall(r'\w+.(\d+)\s(.*)', command_res.stdout.decode('utf-8'))
    result = []
    for if_name_index, if_name in if_names:
        for if_descr_index, if_description in if_descriptions:
            if if_name_index == if_descr_index and if_description:
                result.append({'index': if_name_index, 'name':if_name, 'description':if_description})
    return HttpResponse(json.dumps(result))
    
    
@csrf_exempt
def add_snmp_interfaces(request):
    host = request.POST['host']
    host_obj = Host.objects.get(host = host)
    for key, value in request.POST.items():
        if key != 'host':
            snmpid, name, description = value.split(';')
            try:
                obj = Interface.objects.get(snmpid = int(snmpid), host = host_obj)
            except Interface.DoesNotExist:
                obj = Interface(snmpid = int(snmpid), name=name, description=description, host = host_obj)
                obj.save()
    return HttpResponse("OK")
            
            
@csrf_exempt
def add_interface(request):
    host = request.POST['host']
    host_obj = Host.objects.get(host = host)
    snmpid = request.POST['snmpid']
    name = request.POST['name']
    description = request.POST['description']
    try:
        obj = Interface.objects.get(snmpid = int(snmpid), host = host_obj)
    except Interface.DoesNotExist:
        obj = Interface(snmpid = int(snmpid), name=name, description=description, host = host_obj)
        obj.save()
        return HttpResponse("OK")
    except Exception as err:
        raise Exception(f"Error: {err}")
    else:
        raise Exception(f"Error: Interface already exist ({host} snmpid: {snmpid})")
                

@csrf_exempt    
def update_interface(request):
    interface_id = request.POST['id']
    snmpid = request.POST['snmpid']
    name = request.POST['name']
    description = request.POST['description']
    try:
        obj = Interface.objects.get(id=int(interface_id))
    except Interface.DoesNotExist:
        raise Exception(f"Error: Interface does not exist ({host} snmpid: {snmpid})")
    except Exception as err:
        raise Exception(f"Error: {err}")
    else:
        setattr(obj, 'snmpid', int(snmpid))
        setattr(obj, 'name', name)
        setattr(obj, 'description', description)
        obj.save()
        return HttpResponse("OK")

    
@csrf_exempt    
def update_interface_sampling(request):
    interface_id = request.POST['id']
    sampling = request.POST['sampling']
    try:
        obj = Interface.objects.get(id=int(interface_id))
    except Interface.DoesNotExist:
        raise Exception(f"Error: Interface does not exist ({host} snmpid: {snmpid})")
    else:
        if sampling == 'true':
            setattr(obj, 'sampling', True)
        else:
            setattr(obj, 'sampling', False)
        obj.save()
        return HttpResponse("OK")
    
    
@csrf_exempt  
def delete_interface(request):
    interface_id = request.POST['id']
    Interface.objects.get(id=int(interface_id)).delete()
    return HttpResponse("OK")
    
    
@csrf_exempt   
def get_hosts(request):
    hosts = list(Host.objects.all())
    hosts_json = serializers.serialize('json', hosts)
    return JsonResponse(hosts_json, safe = False)


@csrf_exempt  
def add_host(request):
    host = request.POST['host']
    name = request.POST['name']
    description = request.POST['description']
    flow_path = request.POST['flow_path']
    try:
        obj = Host.objects.get(Q(name = name)|Q(host = host))
    except Host.DoesNotExist:
        obj = Host(name = name, host = host, description = description, flow_path = flow_path)
        obj.save()
        return HttpResponse("OK")
    except Exception as err:
        raise Exception(f"Error: {err}")
    else:
        raise Exception(f"Error: Host already exist ({host} name: {name})")

@csrf_exempt  
def update_host(request):
    host = request.POST['host']
    name = request.POST['name']
    description = request.POST['description']
    flow_path = request.POST['flow_path']
    host_id = request.POST['host_id'];
    try:
        obj = Host.objects.get(id = host_id)
    except Host.DoesNotExist:
        raise Exception(f"Error: Host does not exist ({host} name: {name})")
    except Exception as err:
        raise Exception(f"Error: {err}")
    else:
        setattr(obj, 'host', host)
        setattr(obj, 'name', name)
        setattr(obj, 'description', description)
        setattr(obj, 'flow_path', flow_path)
        obj.save()
        return HttpResponse("OK")

           
@csrf_exempt  
def delete_host(request):
    host_id = request.POST['host_id']
    try:
        Host.objects.get(id=int(host_id)).delete()
    except Host.DoesNotExist:
        raise Exception(f"Error: Host does not exist ({host} name: {name})")
    else:
        return HttpResponse("OK")