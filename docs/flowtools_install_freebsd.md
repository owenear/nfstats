# FlowTools install on FreeBSD

1. Installing 
```
pkg install flow-tools
```
or from ports
```
cd /usr/ports/net-mgmt/flow-tools
make install clean
```
2. Configure it to start with parameter -n (rotations) equals 1439 
(the number of times flow-capture will create a new file per day. That is, every minute)
Add to rc.conf:
```
flow_capture_enable="YES"
flow_capture_localip="10.0.0.10" 
flow_capture_remoteip="10.0.0.1" 
flow_capture_port="9999" 
flow_capture_datadir="/var/flows" 
flow_capture_flags="-z0 -n1439 -N3 -E10G -e0 -S1"
```
Use 'man flow-capture' to read more about it. 
