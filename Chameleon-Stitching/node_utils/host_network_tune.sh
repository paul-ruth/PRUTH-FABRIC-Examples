#!/bin/bash

#dev=$1

#echo dev $dev

# Linux host tuning from https://fasterdata.es.net/host-tuning/linux/
cat >> /etc/sysctl.conf <<EOL
# allow testing with buffers up to 128MB
net.core.rmem_max = 134217728 
net.core.wmem_max = 134217728 
# increase Linux autotuning TCP buffer limit to 64MB
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
# recommended default congestion control is htcp 
net.ipv4.tcp_congestion_control=bbr
# recommended for hosts with jumbo frames enabled
net.ipv4.tcp_mtu_probing=1
# recommended to enable 'fair queueing'
net.core.default_qdisc = fq
EOL

sysctl --system


for dev in `basename -a /sys/class/net/*`; do
    # Turn on jumbo frames
    ip link set dev $dev mtu 9000
done
