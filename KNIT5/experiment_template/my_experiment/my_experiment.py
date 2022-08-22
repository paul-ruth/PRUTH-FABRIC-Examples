#!/bin/python3

import json
import time
from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager

import os
import sys

#module_path = os.path.abspath(os.path.join('..'))
##print(module_path)
#if module_path not in sys.path:
#    sys.path.append(module_path)

#from notebook_utils.utils import *
#from notebook_utils.fablib_plugin_methods import *
#from notebook_utils.fabric_fabnet_slice import *


# Add methods to FABlib Classes
#setattr(Interface, 'get_ip_addr', get_ip_addr)


# Define Experiment
class MyExperiment():

    fablib = None
    slice = None
    slice_id = None
    slice_name = None
    
    def __init__(self, name):
        self.fablib = fablib_manager()
        self.slice = None
        self.slice_id = None
        
    def load(self, name):
        try:
            #self.fablib = fablib_manager()

            #Create Slice
            self.slice_name = name
            self.slice = self.fablib.get_slice(name=self.slice_name)
            self.slice_id = self.slice.get_slice_id()
            
            self.node1_name = 'node1'
            self.node2_name = 'node2'
            
            self.site1 = self.slice.get_node(name=self.node1_name).get_site()
            self.site2 = self.slice.get_node(name=self.node2_name).get_site()

            
            self.net1_name = f'{self.site1}_net'
            self.net2_name = f'{self.site2}_net'
            
        except Exception as e:
            print(f"{e}")            
            
        

    def deploy(self, name=None, site_count=2, node_count=1, node_cores=2, node_ram=8, node_disk=10):

        try:
            #self.fablib = fablib_manager()

            #Create Slice
            self.slice_name = name
            self.slice = self.fablib.new_slice(name=name)

            [self.site1,self.site2] = self.fablib.get_random_sites(count=2)
            print(f"Sites: {self.site1}, {self.site2}")
            
            self.node1_name = 'node1'
            self.node2_name = 'node2'
            
            self.net1_name = f'{self.site1}_net'
            self.net2_name = f'{self.site2}_net'

            # Node1
            node1 = self.slice.add_node(name=self.node1_name, 
                                        site=self.site1, 
                                        cores=node_cores, 
                                        ram=node_ram, 
                                        disk=node_disk)
            iface1 = node1.add_component(model='NIC_Basic', name='nic1').get_interfaces()[0]

            # Node2
            node2 = self.slice.add_node(name=self.node2_name, 
                                        site=self.site2, 
                                        cores=node_cores, 
                                        ram=node_ram, 
                                        disk=node_disk)
            iface2 = node2.add_component(model='NIC_Basic', name='nic1').get_interfaces()[0]

            # NetworkS
            net1 = self.slice.add_l3network(name=self.net1_name, interfaces=[iface1], type='IPv4')
            net2 = self.slice.add_l3network(name=self.net2_name, interfaces=[iface2], type='IPv4')

            #Submit Slice Request
            self.slice_id = self.slice.submit()

        except Exception as e:
            print(f"{e}") 

    def configure(self):
        try:
            network1 = self.slice.get_network(name=self.net1_name)
            network1_available_ips = network1.get_available_ips()
            print(f"{network1}")

            network2 = self.slice.get_network(name=self.net2_name)
            network2_available_ips =  network2.get_available_ips()
            print(f"{network2}")


            node1 = self.slice.get_node(name=self.node1_name)        
            node1_iface = node1.get_interface(network_name=self.net1_name)  
            node1_addr = network1_available_ips.pop(0)
            node1_iface.ip_addr_add(addr=node1_addr, subnet=network1.get_subnet())

            #node1.ip_route_add(subnet=network2.get_subnet(), gateway=network1.get_gateway())
            node1.ip_route_add(subnet=IPv4Network("10.128.0.0/12") , gateway=network1.get_gateway())

            stdout, stderr = node1.execute(f'ip addr show {node1_iface.get_os_interface()}')
            print (stdout)

            stdout, stderr = node1.execute(f'ip route list')
            print (stdout)

            node2 = self.slice.get_node(name=self.node2_name)        
            node2_iface = node2.get_interface(network_name=self.net2_name) 
            node2_addr = network2_available_ips.pop(0)
            node2_iface.ip_addr_add(addr=node2_addr, subnet=network2.get_subnet())

            #node2.ip_route_add(subnet=network1.get_subnet(), gateway=network2.get_gateway())
            node2.ip_route_add(subnet=IPv4Network("10.128.0.0/12") , gateway=network2.get_gateway())


            stdout, stderr = node2.execute(f'ip addr show {node2_iface.get_os_interface()}')
            print (stdout)

            stdout, stderr = node2.execute(f'ip route list')
            print (stdout)
        except Exception as e:
            print(f"{e}") 

    def run(self):
        try:
            node1 = self.slice.get_node(name=self.node1_name)  
            node2 = self.slice.get_node(name=self.node2_name)  
            node2_iface = node2.get_interface(network_name=self.net2_name) 

            node2_addr = node2_iface.get_ip_addr()
            
            #print(f"node2_addr: {node2_addr}")
            
            #stdout, stderr = node1.execute(f'ping -c 5 {node2_addr}')
            #print (stdout)
            #print (stderr)
            
            run_iperf3(source_node=node1, target_node=node2, target_ip=node2_addr, w='32M', P=1, t=60, i=10)
        except Exception as e:
            print(f"{e}") 
            
        return node1


    def results(self):
        try:
            pass
        except Exception as e:
            print(f"{e}") 


    def clean_up(self):
        try:
            self.fablib.delete_slice(slice_name=self.slice_name)
            
            self.slice = None
            self.slice_id = None
        except Exception as e:
            print(f"Exception: {e}")



