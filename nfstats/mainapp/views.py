from django.shortcuts import render
from django.http import HttpResponse
from .models import *
from datetime import datetime
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt


# Create your views here.


def date_tranform(date):
    date_re = re.match(r'(\d+).(\d+).(\d+)\s(\d+):(\d+)', date)
    return f"{date_re.group(3)}-{date_re.group(2)}-{date_re.group(1)}.{date_re.group(4)}{date_re.group(5)}"


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
    return render(request, "mainapp/settings/settings_hosts.html", {'hosts' : hosts} )


@csrf_exempt
def settings_system(request):
    #settings = Settings.objects.all()
    return render(request, "mainapp/settings/settings_system.html")

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