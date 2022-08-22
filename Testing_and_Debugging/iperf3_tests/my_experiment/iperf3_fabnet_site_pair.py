#!/bin/python3

import json
import time
from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager

import os
import sys

from datetime import datetime
from dateutil import tz


module_path = os.path.abspath(os.path.join(f"{os.environ['HOME']}/work/fablib_local"))
if module_path not in sys.path:
    sys.path.append(module_path)
from fablib_custom.fablib_custom import *
from performance_testing.iperf3 import *

from fablib_common_utils.utils import *
from fablib_common_utils.fabric_fabnet_slice import *


# Define Experiment
class MyExperiment():

    fablib = None
    slice = None
    slice_id = None
    slice_name = None
    
    sites=[]
    
    def __init__(self, 
                 name, 
                 output_type='HTML', 
                 node_tools_dir="node_tools", 
                 sites=None, 
                 node_cores=2, 
                 node_ram=8, 
                 node_disk=10, 
                 nic_type='NIC_Basic'):
        
        self.fablib = fablib_manager(output_type=output_type)
        self.slice = None
        self.slice_id = None
        self.name = name
        
        self.node_tools_dir=node_tools_dir
        self.sites=sites
        self.node_cores=node_cores
        self.node_ram=node_ram
        self.node_disk=node_disk
        self.nic_type=nic_type

        # Used for creating unique run/slice IDs for this experiment
        self.timestamp = time_stamp = datetime.now(tz=tz.tzutc()).strftime('%Y%m%d%H%M')
        
        self.slice_name = f"{self.name}_{self.timestamp}"


        
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
            
    def deploy(self):

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
            
    def deploy_manual(self):

        try:
            #self.fablib = fablib_manager()
            #Create Slice          
            self.slice = self.fablib.new_slice(name=self.slice_name)
            
            for site in self.sites:
                print(f"Adding node at {site}")
                node_name = f'{site}_node1'
                net_name = f'{site}_net'

                # Node1
                node = self.slice.add_node(name=node_name, 
                                            site=site, 
                                            cores=self.node_cores, 
                                            ram=self.node_ram, 
                                            disk=self.node_disk)
                iface = node.add_component(model=self.nic_type, name='nic1').get_interfaces()[0]

                # Network
                net1 = self.slice.add_l3network(name=net_name, interfaces=[iface], type='IPv4')

            #Submit Slice Request
            self.slice_id = self.slice.submit()

        except Exception as e:
            print(f"{e}") 
            raise e            
        

    def deployXXX(self, site_count=2, sites=None, node_count=1, node_cores=2, node_ram=8, node_disk=10):

        try:
            #self.fablib = fablib_manager()

            #Create Slice
            #self.slice_name = name
            self.slice = self.fablib.new_slice(name=self.name)
            
            if sites == None:
                [self.site1,self.site2] = self.fablib.get_random_sites(count=2, avoid=self.avoid)
            else:
                [self.site1,self.site2] = sites
                
            print(f"Sites: {self.site1}, {self.site2}")
            
            self.node1_name = f'{self.site1}1'
            self.node2_name = f'{self.site2}1'
            
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
            raise e

    def configure(self):
        try:
            threads = {}
            for node in self.slice.get_nodes():
                print(f"Uploading {self.node_tools_dir} to {node.get_name()}")
                node.upload_directory(self.node_tools_dir, ".")
                node.execute('chmod +x fabric_node_tools/*.sh')
                
                node_nic_name=f"{node.get_name()}-nic1-p1"
                dev = node.get_interface(name=node_nic_name).get_os_interface()

                threads[node] = node.execute_thread(f"sudo ./fabric_node_tools/host_config_redhat.sh && sudo ./fabric_node_tools/host_tune_redhat.sh {dev}")
            
            for node,thread in threads.items():
                print(f"Waiting for {node.get_name()}")
                thread.result()
            
        except Exception as e:
            print(f"{e}") 
            
    def run(self, run_name='', runs = [], O=1, w='32M', P=1, t=60, i=10):
        try:
            output_file=f'{self.name}_{self.timestamp}_{run_name}'
            for source_site,target_site in runs: 
                print(f"source_site: {source_site}")
                print(f"target_site: {target_site}")

                source_node_name = f"{source_site}_node1"
                source_node = self.slice.get_node(name=source_node_name)  

                target_node_name = f"{target_site}_node1"
                target_network_name = f"{target_site}_net"
                target_node = self.slice.get_node(name=target_node_name)  
                target_ip = target_node.get_interface(network_name=target_network_name).get_ip_addr()

                print(f'source_node: {source_node.get_name()}')
                print(f'target_node: {target_node.get_name()}')
                print(f'target_ip: {target_ip}')

                iperf3_run(source_node=source_node, 
                           target_node=target_node, 
                           target_ip=target_ip, 
                           w=w, P=P, t=t, i=i, verbose=True)
            
            
            
        except Exception as e:
            print(f"{e}") 
            


    def runXXX(self, output_file='output.txt', source_node_name=None, target_node_name=None, O=1, w='32M', P=1, t=60, i=10):
        try:
            node1 = self.slice.get_node(name=source_node_name)  
            node2 = self.slice.get_node(name=target_node_name)  
            node2_iface = node2.get_interface(network_name=self.net2_name) 

            node2_addr = node2_iface.get_ip_addr()
            
            #stdout, stderr = node1.execute(f'ping -c 5 {node2_addr}', quiet=False)
            #print (stdout)
            #print (stderr)
            
            iperf3_run(source_node=node1, target_node=node2, target_ip=node2_addr, w='32M', P=1, t=60, i=10)
            #iperf3_run(source_node=None, target_node=None, target_ip=None, w=None, P=1, t=60, i=10, O=None, verbose=False):
            
            #file = open(output_file, "w")
            #file.write(stdout)
            #file.close()
            
            
            
        except Exception as e:
            print(f"{e}") 
            


    def results(self):
        try:
            iperf3_process_output(verbose=True)
        except Exception as e:
            print(f"{e}") 


    def clean_up(self):
        try:
            self.fablib.delete_slice(slice_name=self.slice_name)
            
            self.slice = None
            self.slice_id = None
        except Exception as e:
            print(f"Exception: {e}")



