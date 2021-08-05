from django.shortcuts import render
from .models import Host, Interface
from django.utils import timezone
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from .settings_sys import SYS_SETTINGS
from pprint import pprint
from random import getrandbits
from collections import namedtuple
from django.db.models import Q
import re


@csrf_exempt
def common(request):
    if not request.session.get('session_id'):
        request.session['session_id'] = getrandbits(16)
    hosts = Host.objects.all()
    if hosts:
        host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
        direction = request.GET['direction'] if request.GET.get('direction') else 'input'
        if request.GET.get('aggregate'):
            Aggregate_interface = namedtuple("Aggregate_interface", "name description snmpid")
            snmpid_aggregate = re.findall(r'\d+', request.GET.get('aggregate'))
            name_aggregate = ''
            for snmpid in snmpid_aggregate:
                name_aggregate += Interface.objects.get(host=host_selected, sampling=True, snmpid = snmpid).name + ', '
            interfaces = [ Aggregate_interface(name_aggregate[:-2], "Aggregate Interface", "aggregate") ]
        else:
            interfaces = Interface.objects.filter(host=host_selected, sampling=True).order_by('snmpid')
        date = (timezone.now() - timedelta(minutes=2)).isoformat()
        return render(request, "mainapp/common.html", {'date' : date, 'hosts' : hosts, 'host_selected' : host_selected,
                                                      'interfaces' : interfaces, 'direction' : direction, 'aggregate' : request.GET.get('aggregate') } )
    else:
        return render(request, "mainapp/settings/settings_hosts.html", {'hosts' : hosts} )    


@csrf_exempt
def interface(request):
    hosts = Host.objects.all()
    host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
    interfaces = Interface.objects.filter(host=host_selected, sampling=False).order_by('name')
    direction = request.GET['direction'] if request.GET.get('direction') else 'input'
    date = (timezone.now() - timedelta(minutes=2)).isoformat()
    return render(request, "mainapp/interface.html", {'date' : date, 'hosts' : hosts, 'host_selected' : host_selected,
                                                      'interfaces' : interfaces, 'direction' : direction } )
        

@csrf_exempt
def bgp_as(request):
    hosts = Host.objects.all()
    host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
    direction = request.GET['direction'] if request.GET.get('direction') else 'input'
    date = (timezone.now() - timedelta(minutes=2)).isoformat()
    return render(request, "mainapp/bgp-as.html", {'date' : date, 'hosts' : hosts, 'host_selected' : host_selected, 'direction' : direction } )


@csrf_exempt
def ip(request):
    hosts = Host.objects.all()
    host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
    direction = request.GET['direction'] if request.GET.get('direction') else 'input'
    ip_type = request.GET['ip_type'] if request.GET.get('ip_type') else 'ip-destination-address'
    date = (timezone.now() - timedelta(minutes=2)).isoformat()
    return render(request, "mainapp/ip.html", {'date' : date, 'hosts' : hosts, 'host_selected' : host_selected, 'direction' : direction, 'ip_type' : ip_type } )


@csrf_exempt
def settings_hosts(request):
    hosts = Host.objects.all()
    return render(request, "mainapp/settings/settings_hosts.html", {'hosts' : hosts } )

@csrf_exempt
def settings_system(request):
    return render(request, "mainapp/settings/settings_system.html",  {'settings' : SYS_SETTINGS })

@csrf_exempt
def settings_interfaces(request):
    hosts = Host.objects.all()
    if hosts:
        host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
        interfaces = Interface.objects.filter(host=host_selected).order_by('snmpid')
        return render(request, "mainapp/settings/settings_interfaces.html", {'hosts' : hosts, 'host_selected' : host_selected,
                                                                    'interfaces' : interfaces} )
    else:
        return render(request, "mainapp/settings/settings_hosts.html", {'hosts' : hosts} )