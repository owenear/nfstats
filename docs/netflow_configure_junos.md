# NetFlow v5 configure example in JunOS

1. Configure sampling in forwarding options:
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
```
2. Configure sampling in uplink interfaces:
```
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