# NFStats
The web-based tool for calculating and displaying network traffic statistics for ISPs.
It uses flow-capture, flow-report, flow-nfilter, flow-print from flow-tools package to analyse NetFlow data and google-charts for display graphs.

### Prerequisites
- FreeBSD or GNU/Linux
- flow-tools
- Python 3.6, Django 3.2 
- One of the Django supported databases:
  - PostgreSQL 9.6 and higher (psycopg2 2.5.4 or higher is required) 
  - MySQL 5.7 and higher.
  - Oracle Database Server versions 12.2 and higher. Version 6.0 or higher of the cx_Oracle Python driver is required. 
  

1. Configure NetFlow v5 on a network device with active timeout 60 sec.
Example for JunOS
```
forwarding-options {
    sampling {
        input {
            rate 2000;
            run-length 0;
        }
        family inet {
            output {
                flow-inactive-timeout 15;
                flow-active-timeout 60; 
                flow-server 10.0.0.10 {
                    port 9999;
                    autonomous-system-type origin;
                    source-address 10.0.0.1;
                    version 5;
                }
            }
        }
    }
}

Add sampling to the uplink interfaces:

ae0 {
...
  unit 0 {
  ...
    family inet {
    ...
      sampling {
         input;
         output;
      }
    }
  }
}

```
2. Install flow-tools on a server.
For the FreeBSD
```
pkg install flow-tools
```
or
```
cd /usr/ports/net-mgmt/flow-tools
make install clean
``` 
for the GNU/Linux build from source (https://code.google.com/archive/p/flow-tools/)

And configure it to start with parameter -n (rotations) equals 1439 (the number of times flow-capture will create a new
file per day. That is, every minute)
Example of FreeBSD rc.conf:
```
flow_capture_enable="YES"
flow_capture_localip="10.0.0.10" 
flow_capture_remoteip="10.0.0.1" 
flow_capture_port="9999" 
flow_capture_datadir="/var/flows" 
flow_capture_flags="-z0 -n1439 -N3 -E10G -e0 -S1"
```
Use 'man flow-capture' to read more about it. 

### Installation



 
