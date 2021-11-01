# NFDUMP install on Ubuntu

1. Installing 
```
sudo apt install nfdump
```
2. Make changes to /etc/nfdump/default.conf
```
options='-z -t 60 -w -D -T all -l /var/flows/ -I any -S 1 -P /var/run/nfcapd.allflows.pid -p 9999 -b 10.0.0.10 -e 10G'
```

Use 'man nfcapd' to read more about it. 
