#!/bin/python3

import json
import time
from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager

import os
import sys
import random

from datetime import datetime
from dateutil import tz



module_path = os.path.abspath(os.path.join(f"{os.environ['HOME']}/work/fablib_local"))
if module_path not in sys.path:
    sys.path.append(module_path)
#from fablib_custom.fablib_custom import *
#from performance_testing.iperf3 import *

from fablib_common_utils.utils import *
from fablib_common_utils.fabric_fabnet_slice import *


# Define Experiment
class MyExperiment():

    fablib = None
    slice = None
    slice_id = None
    slice_name = None
    
    sites=[]
    
    @staticmethod
    def deploy_and_run(name, 
                         output=None, 
                         node_tools_dir="node_tools", 
                         site1=None,
                         site2=None,
                         host1=None,
                         host2=None,
                         node_cores=2, 
                         node_ram=8, 
                         node_disk=10, 
                         nic_type='NIC_Basic',
                         avoid=[]):
        
        my_experiment = MyExperiment(name,
                                         output=None,
                                         site1=site1,
                                         site2=site2,
                                         host1=host1,
                                         host2=host2,
                                         node_cores=node_cores, 
                                         node_ram=node_ram, 
                                         node_disk=node_disk, 
                                         nic_type=nic_type,
                                         avoid=avoid,
                                         node_tools_dir=node_tools_dir)
        
        my_experiment.deploy(progress=False)
        my_experiment.configure()
        results = my_experiment.run()
        
        my_experiment.clean_up()

        return results
    
    
    def __init__(self, 
                 name, 
                 output=None, 
                 node_tools_dir="node_tools", 
                 site1=None,
                 site2=None,
                 host1=None,
                 host2=None,
                 node_cores=2, 
                 node_ram=8, 
                 node_disk=10, 
                 nic_type='NIC_Basic',
                 avoid=[]):
        
        self.fablib = fablib_manager(output=output)
        self.slice = None
        self.slice_id = None
        self.name = name
        
        print(f"Creating: {self.name}")
        
        self.node_tools_dir=node_tools_dir
        
        if site1 == None and site2 == None :
            print(f"1 site1 {site1}, host: {host1}")

            [site1,site2] = self.fablib.get_random_sites(count=2,avoid=avoid)
            
        if site1 == None:
            print(f"2 site1 {site1}, host: {host1}")

            [site1] = self.fablib.get_random_site(avoid=avoid+[site2])
        
        if site2 == None:
            print(f"3 site1 {site1}, host: {host1}")

            [site2] = self.fablib.get_random_site(avoid=avoid+[site1])
        
        
        if host1 == None:
            site1_hosts = self.fablib.get_resources().get_host_capacity(site1)
            host1 = f'{site1.lower()}-w{random.randint(1,site1_hosts)}.fabric-testbed.net'

        if host2 == None:
            site2_hosts = self.fablib.get_resources().get_host_capacity(site2)
            host2 = f'{site2.lower()}-w{random.randint(1,site2_hosts)}.fabric-testbed.net'

                                         
        
        #print(f"site1 {site1}, host: {host1}")
        #print(f"site2 {site2}, host: {host2}")
        
        self.site1=site1
        self.site2=site2
        self.host1=host1
        self.host2=host2        
        self.node_cores=node_cores
        self.node_ram=node_ram
        self.node_disk=node_disk
        self.nic_type=nic_type
        
        
        print(f"{self.name}:  site1 {self.site1}, host1: {self.host1}, site2 {self.site2}, host2: {self.host2}")
        
        # Used for creating unique run/slice IDs for this experiment
        self.timestamp = time_stamp = datetime.now(tz=tz.tzutc()).strftime('%Y%m%d%H%M')
        
        self.slice_name = f"{self.name}_{self.timestamp}"


        
    def load(self, name):
        pass

    def deploy_auto(self):

        try:
            self.slice = create_fabnet_slice(name=self.slice_name, 
                        node_count=1, 
                        sites=self.sites, 
                        cores=self.node_cores, 
                        ram=self.node_ram, 
                        disk=self.node_disk)
        
        except Exception as e:
            print(f"{e}") 
            raise e            
            
    def deploy(self, progress=True):

        try:
            #self.fablib = fablib_manager()
            #Create Slice          
            self.slice = self.fablib.new_slice(name=self.name)
            
            
            #print(f"Adding node1 at {self.site1}")
            self.node1_name = f'{self.site1}_node1'
            self.network1_name = f'{self.site1}_net1'

            # Node1
            node = self.slice.add_node(name=self.node1_name, 
                                        site=self.site1,
                                        host=self.host1,
                                        cores=self.node_cores, 
                                        ram=self.node_ram, 
                                        disk=self.node_disk)
            iface = node.add_component(model=self.nic_type, name='nic1').get_interfaces()[0]

            # Network
            net1 = self.slice.add_l3network(name=self.network1_name, interfaces=[iface], type='IPv4')

            
            
            #print(f"Adding node2 at {self.site2}")
            self.node2_name = f'{self.site2}_node2'
            self.network2_name = f'{self.site2}_net2'
             # Node2
            node = self.slice.add_node(name=self.node2_name, 
                                        site=self.site2, 
                                        host=self.host2,
                                        cores=self.node_cores, 
                                        ram=self.node_ram, 
                                        disk=self.node_disk)
            iface = node.add_component(model=self.nic_type, name='nic1').get_interfaces()[0]

            # Network
            net2 = self.slice.add_l3network(name=self.network2_name, interfaces=[iface], type='IPv4')
            

            #print(f"Submit")

            #Submit Slice Request
            self.slice_id = self.slice.submit(progress=progress)

        except Exception as e:
            print(f"{e}") 
            raise e            
        

        
    def configure(self):
        try:
            network1 = self.slice.get_network(name=self.network1_name)
            network1_available_ips = network1.get_available_ips()
            #network1.show()
            
            network2 = self.slice.get_network(name=self.network2_name)
            network2_available_ips =  network2.get_available_ips()
            #network2.show()
        except Exception as e:
            print(f"Exception: {e}")
            

        try:
            node1 = self.slice.get_node(name=self.node1_name)        
            node1_iface = node1.get_interface(network_name=self.network1_name)  
            self.node1_addr = network1_available_ips.pop(0)
            node1_iface.ip_addr_add(addr=self.node1_addr, subnet=network1.get_subnet())

            node1.ip_route_add(subnet=network2.get_subnet(), gateway=network1.get_gateway())

            stdout, stderr = node1.execute(f'ip addr show {node1_iface.get_os_interface()}')
            #print (stdout)

            stdout, stderr = node1.execute(f'ip route list')
            #print (stdout)
        except Exception as e:

            print(f"Exception: {e}")

        try:
            node2 = self.slice.get_node(name=self.node2_name)        
            node2_iface = node2.get_interface(network_name=self.network2_name) 
            self.node2_addr = network2_available_ips.pop(0)
            node2_iface.ip_addr_add(addr=self.node2_addr, subnet=network2.get_subnet())

            node2.ip_route_add(subnet=network1.get_subnet(), gateway=network2.get_gateway())

            stdout, stderr = node2.execute(f'ip addr show {node2_iface.get_os_interface()}')
            #print (stdout)

            stdout, stderr = node2.execute(f'ip route list')
            #print (stdout)
        except Exception as e:
            print(f"Exception: {e}")
            
    def run(self):
        try:
            node1 = self.slice.get_node(name=self.node1_name)        

            #stdout, stderr = node1.execute(f'ping -c 5 {node2_addr}', quiet=False)
            #stdout, stderr = node1.execute(f'ping {node2_addr}', quiet=False)
            #stdout, stderr = node1.execute(f'ping -c 5 {node2_addr} > file 2>&1; echo $?', quiet=False)
            stdout, stderr = node1.execute(f'ping -c 5 {self.node2_addr} > file 2>&1; echo $?')
            #stdout, stderr = node1.execute(f'ping -c 5 127.0.0.1; echo $?', quiet=False)

            if stdout.strip() == '0':
                result = 'success'
                #print(f"success")  #worked
            else:
                result = 'fail'
                #print(f"fail")   #failed


            return f"{self.slice.get_name()},{self.node1_name},{self.host1},{self.node2_name},{self.host2},{result}"

        except Exception as e:
            print(f"Exception: {e}")




    def results(self):
        try:
            iperf3_process_output(verbose=True)
        except Exception as e:
            print(f"{e}") 


    def clean_up(self):
        try:
            self.fablib.delete_slice(slice_name=self.name)
            
            self.slice = None
            self.slice_id = None
        except Exception as e:
            print(f"Exception: {e}")



