# FlowTools install on Ubuntu

1. Install dependencies
```
sudo apt install build-essential tcpd zlib1g-dev
```
1. Get the last Flow-Tools package
```
mkdir ~/src
wget https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/flow-tools/flow-tools-0.68.5.1.tar.bz2
```
3. Unpack and install
```
tar -xf flow-tools-0.68.5.1.tar.bz2
cd flow-tools-0.68.5.1
./configure
make install clean
```
4. Add system user for flow-tools daemon
```
adduser --system --no-create-home --shell /usr/sbin/nologin --group flow-tools
```
5. Create directory for netflow data
```
mkdir /var/flows
chown -R flow-tools:flow-tools /var/flows
```
6. Create systemd unit for the flow-capture service with specific parameters (see the flow-capture docs) 
```
# cat /etc/systemd/system/flow-capture.service 
[Unit]
  Description=flow-capture

[Service]
  ExecStart=/usr/local/flow-tools/bin/flow-capture -z0 -n1439 -N3 -E10G -e0 -S1 -w /var/flows -D -p - 10.0.0.1/10.0.0.10/9991
  User=flow-tools
  Group=flow-tools
  Restart=on-failure
 
[Install]
  WantedBy=multi-user.target
```
7. Enable and start service
```
sudo systemctl daemon-reload
sudo systemctl start flow-capture
sudo systemctl enable flow-capture
```