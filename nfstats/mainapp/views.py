from django.shortcuts import render
from django.http import HttpResponse
from .models import Settings, Host, Interface, Speed
from datetime import datetime
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from .settings_sys import SYS_SETTINGS


@csrf_exempt
def common(request):
    hosts = Host.objects.all()
    if hosts:
        host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
        direction = request.GET['direction'] if request.GET.get('direction') else 'input'
        interfaces = Interface.objects.filter(host=host_selected, sampling=True).order_by('snmpid')
        date = (datetime.now() - timedelta(minutes=2)).strftime("%d.%m.%Y %H:%M")
        return render(request, "mainapp/common.html", {'date' : date, 'hosts' : hosts, 'host_selected' : host_selected,
                                                      'interfaces' : interfaces, 'direction' : direction} )
    else:
        return render(request, "mainapp/settings/settings_hosts.html", {'hosts' : hosts} )    


@csrf_exempt
def interface(request):
    hosts = Host.objects.all()
    host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
    direction = request.GET['direction'] if request.GET.get('direction') else 'input'
    date = (datetime.now() - timedelta(minutes=2)).strftime("%d.%m.%Y %H:%M")
    return render(request, "mainapp/interface.html", {'date' : date, 'hosts' : hosts, 'host_selected' : host_selected,
                                                      'direction' : direction } )
        

@csrf_exempt
def bgp_as(request):
    hosts = Host.objects.all()
    host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
    direction = request.GET['direction'] if request.GET.get('direction') else 'input'
    date = (datetime.now() - timedelta(minutes=2)).strftime("%d.%m.%Y %H:%M")
    return render(request, "mainapp/bgp-as.html", {'date' : date, 'hosts' : hosts, 'host_selected' : host_selected, 'direction' : direction } )


@csrf_exempt
def ip(request):
    hosts = Host.objects.all()
    host_selected = Host.objects.filter(host=request.GET['host']).first() if request.GET.get('host') else hosts[0]
    direction = request.GET['direction'] if request.GET.get('direction') else 'input'
    ip_type = request.GET['ip_type'] if request.GET.get('ip_type') else 'ip-destination-address'
    date = (datetime.now() - timedelta(minutes=2)).strftime("%d.%m.%Y %H:%M")
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