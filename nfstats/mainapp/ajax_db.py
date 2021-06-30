from django.http import HttpResponse
from django.http import JsonResponse
from django.core import serializers
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from .models import Settings, Host, Interface, Speed
from .settings_sys import SYS_SETTINGS, VARS, update_globals, logger
import json
import re
import subprocess


@csrf_exempt
def get_snmp_interfaces(request):
    host = request.POST['host']
    command = f"{VARS['snmp_walk']} -v{SYS_SETTINGS['snmp_ver']} -Oseqn -c {SYS_SETTINGS['snmp_com']} {host} .1.3.6.1.2.1.2.2.1.2"
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if command_res.stderr:
        logger.error(f"(SH): {command_res.stderr}")
        raise Exception(f"Error in shell: {command_res.stderr}")
    if_names = re.findall(r'\w+.(\d+)\s\"?([^\"\n]*)\"?', command_res.stdout.decode('utf-8'))
    command = f"{VARS['snmp_walk']} -v{SYS_SETTINGS['snmp_ver']} -Oseqn -c {SYS_SETTINGS['snmp_com']} {host} .1.3.6.1.2.1.31.1.1.1.18"
    command_res = subprocess.run([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if command_res.stderr:
        raise Exception(f"Error in shell: {command_res.stderr}")
    if_descriptions = re.findall(r'\w+.(\d+)\s\"?([^\"\n]*)\"?', command_res.stdout.decode('utf-8'))
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
    result = JsonResponse({"result": "Interfaces added"})
    result.status_code = 200
    return result
            
            
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
        result = JsonResponse({"result": "Interface added"})
        result.status_code = 200
        return result
    except Exception as err:
        logger.error(f"(DB): {err}")
        raise Exception(f"Error: {err}")
    else:
        logger.error(f"(DB): Interface already exist ({host} snmpid: {snmpid})")
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
        logger.error(f"(DB): Interface does not exist ({host} snmpid: {snmpid})")
        raise Exception(f"Error: Interface does not exist ({host} snmpid: {snmpid})")
    except Exception as err:
        logger.error(f"(DB): {err}")
        raise Exception(f"Error: {err}")
    else:
        setattr(obj, 'snmpid', int(snmpid))
        setattr(obj, 'name', name)
        setattr(obj, 'description', description)
        obj.save()
        result = JsonResponse({"result": "Interface updated"})
        result.status_code = 200
        return result

    
@csrf_exempt    
def update_interface_sampling(request):
    interface_id = request.POST['id']
    sampling = request.POST['sampling']
    try:
        obj = Interface.objects.get(id=int(interface_id))
    except Interface.DoesNotExist:
        logger.error(f"(DB): Interface does not exist ({host} snmpid: {snmpid})")
        raise Exception(f"Error: Interface does not exist ({host} snmpid: {snmpid})")
    else:
        if sampling == 'true':
            setattr(obj, 'sampling', True)
        else:
            setattr(obj, 'sampling', False)
        obj.save()
        result = JsonResponse({"result": "Interface updated"})
        result.status_code = 200
        return result
    
    
@csrf_exempt  
def delete_interface(request):
    interface_id = request.POST['id']
    Interface.objects.get(id=int(interface_id)).delete()
    result = JsonResponse({"result": "Interface deleted"})
    result.status_code = 200
    return result
    
    
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
        result = JsonResponse({"result": "Host added"})
        result.status_code = 200
        return result
    except Exception as err:
        logger.error(f"(DB): {err}")
        raise Exception(f"Error: {err}")
    else:
        logger.error(f"(DB): Host already exist ({host} name: {name})")
        raise Exception(f"Error: Host already exist ({host} name: {name})")


@csrf_exempt  
def update_host(request):
    host = request.POST['host']
    name = request.POST['name']
    description = request.POST['description']
    flow_path = request.POST['flow_path']
    host_id = request.POST['host_id']
    try:
        obj = Host.objects.get(id = host_id)
    except Host.DoesNotExist:
        logger.error(f"(DB): Host does not exist ({host} name: {name})")
        raise Exception(f"Error: Host does not exist ({host} name: {name})")
    except Exception as err:
        logger.error(f"(DB): {err}")
        raise Exception(f"Error: {err}")
    else:
        setattr(obj, 'host', host)
        setattr(obj, 'name', name)
        setattr(obj, 'description', description)
        setattr(obj, 'flow_path', flow_path)
        obj.save()
        result = JsonResponse({"result": "Host updated"})
        result.status_code = 200
        return result


           
@csrf_exempt  
def delete_host(request):
    host_id = request.POST['host_id']
    try:
        Host.objects.get(id=int(host_id)).delete()
    except Host.DoesNotExist:
        logger.error(f"(DB): Host does not exist ({host} name: {name})")
        raise Exception(f"Error: Host does not exist ({host} name: {name})")
    else:
        result = JsonResponse({"result": "Host deleted"})
        result.status_code = 200
        return result


@csrf_exempt  
def update_settings(request):
    vars = { 
        'log_dir' :  request.POST['log_dir'], 
        'flowtools_bin' : request.POST['flowtools_bin'],
        'snmp_bin' : request.POST['snmp_bin'],
        'snmp_com' : request.POST['snmp_com'],
        'history_days' : request.POST['history_days'],
    }
    for name, value in vars.items():
        try:
            obj = Settings.objects.get(name = name)
        except Settings.DoesNotExist:
            obj = Settings(name = name, value = value)
            obj.save()
        except Exception as err:
            logger.error(f"(DB): {err}")
            raise Exception(f"Error: {err}")
        else:
            setattr(obj, 'value', value)
            obj.save()
    update_globals()
    result = JsonResponse({"result": "Settings updated"})
    result.status_code = 200
    return result