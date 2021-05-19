from django.urls import path
from . import views
from . import ajax
from . import ajax_db

urlpatterns = [
    path('', views.common, name="common"),
    path('interface', views.interface, name="interface"),
    path('bgp-as', views.bgp_as, name="bgp-as"),
    path('ip', views.ip, name="ip"),   
    
    path('settings', views.settings_hosts, name="settings_hosts"),
    path('settings/interfaces/', views.settings_interfaces, name="settings_interfaces"),
    path('settings/system/', views.settings_system, name="settings_system"),
    
    path('get_pie_chart_data', ajax.get_pie_chart_data),
    path('get_interface_chart_data', ajax.get_interface_chart_data),
    path('get_as_chart_data', ajax.get_as_chart_data),
    path('get_ip_chart_data', ajax.get_ip_chart_data),
    path('get_ip_traffic_data', ajax.get_ip_traffic_data),

    path('get_snmp_interfaces', ajax_db.get_snmp_interfaces),
    path('add_snmp_interfaces', ajax_db.add_snmp_interfaces),
    path('add_interface', ajax_db.add_interface),
    path('update_interface_sampling', ajax_db.update_interface_sampling),
    path('update_interface', ajax_db.update_interface),
    path('delete_interface', ajax_db.delete_interface),
    
    path('get_hosts', ajax_db.get_hosts),
    path('add_host', ajax_db.add_host),
    path('update_host', ajax_db.update_host),
    path('delete_host', ajax_db.delete_host),
]

