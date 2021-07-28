# NFDUMP install on FreeBSD

1. Installing 
```
pkg install nfdump
```
or from ports (configure it with nfcapd collector)
```
cd /usr/ports/net-mgmt/nfdump
make configure
make install clean
```
2. Unfortunately, the installation of nfdump does not create the service for the "nfcapd" collector.
So you have to create script in /usr/local/etc/rc.d/ on your own (example below).  
Configure "nfcapd" to rotate files every minute.  

```
#!/bin/sh

case "$1" in
start)
  nfcapd -z -t 60 -w -D -T all -l /var/flows/ -I any -S 1 -P /var/run/nfcapd.allflows.pid -p 9999 -b 10.0.0.10 -e 10G
  ;;
stop)
  /usr/bin/killall -9 nfcapd
  ;;
  
*)
  echo "use nfcapd start|stop"
  ;;
esac

exit 0
```
Use 'man nfcapd' to read more about it. 