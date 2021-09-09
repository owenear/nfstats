from django.db import models

# Create your models here.
class Settings(models.Model):
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    def __str__(self):
        return self.name + ' = ' + self.value

class Host(models.Model):
    name = models.CharField(max_length=255)
    host = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True, default=None)
    flow_path = models.CharField(max_length=255)
    snmp_com = models.CharField(max_length=255, default='public') 
    def __str__(self):
        return self.name

class Interface(models.Model):
    snmpid = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True, default=None)
    host = models.ForeignKey(Host, on_delete = models.CASCADE)
    sampling = models.BooleanField(default=False) 
    def __str__(self):
        return self.host.name + '.' + self.name + ' (' + self.description + ')'
    
class Speed(models.Model):
    in_bps = models.BigIntegerField()
    out_bps = models.BigIntegerField()
    date = models.DateTimeField()
    interface = models.ForeignKey(Interface, on_delete = models.CASCADE)