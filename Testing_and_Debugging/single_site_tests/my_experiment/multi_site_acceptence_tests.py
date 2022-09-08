#!/bin/python3

import json
import time
from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager

from datetime import datetime
from dateutil import tz

import os
import sys

module_path = os.path.abspath(os.path.join(f"{os.environ['HOME']}/work/fablib_local"))
if module_path not in sys.path:
    sys.path.append(module_path)
#from fablib_custom.fablib_custom import *
#from performance_testing.iperf3 import *

# Define Experiment
class MyExperiment():

    fablib = None
    slice = None
    slice_id = None
    slice_name = None
    
    def __init__(self, name, output_type='HTML', node_tools="node_tools"):
        self.fablib = fablib_manager(output_type=output_type)
        #self.fablib = fablib_manager()
        self.slice = None
        self.slice_id = None
        self.node_tools=node_tools
        self.name = name
        
        # Used to create unique names
        self.timestamp = time_stamp = datetime.now(tz=tz.tzutc()).strftime('%Y%m%d%H%M')

        # Used for cleanup
        self.slice_names = []
        
        
    def wait_jupyter(self):
        self.slice = self.fablib.get_slice(name=self.slice_name)
        self.slice.wait_jupyter()
        
    def load(self, name):
        try:
            #self.fablib = fablib_manager()

            #Create Slice
            self.slice_name = name
            self.slice = self.fablib.get_slice(name=self.slice_name)
            self.slice_id = self.slice.get_slice_id()
            
        except Exception as e:
            print(f"{e}")    
        
    def list_resources(self):
        self.fablib.get_resources().list()        
        
    def test1_create_simple_nodes(self, 
                                  name='testing', 
                                  site=None, 
                                  hosts=None, 
                                  count=1, 
                                  cores=2,
                                  ram=8,
                                  disk=10,
                                  image='default_rocky_8'): 
        self.slice_name = f'test1_{name}_{self.timestamp}'
        
        slice = self.fablib.new_slice(name=self.slice_name)

        if hosts == None:
            for i in range(count):
                node_name = f"{site}_node{i+1}"

                slice.add_node( name=node_name, 
                                site=site,
                                cores=cores,
                                ram=ram,
                                disk=disk, 
                                image=image)
        else:
            for host in hosts:
                for i in range(count):
                    node_name = f"{host}_node{i+1}"

                    slice.add_node(name=node_name, 
                                   site=site, 
                                   host=host, 
                                   cores=cores,
                                   ram=ram,
                                   disk=disk, 
                                   image=image)
                
        self.slice_names.append(self.slice_name)
        
        slice_id = slice.submit()
        
        for node in slice.get_nodes():
            print(f"{node.get_name()}:")
            stdout, stderr = node.execute('echo Hello, FABRIC from node `hostname -s`', quiet=False)
        
        return slice
    
    def test2_create_nodes_L2bridge(self, 
                                    name='testing', 
                                    site=None, 
                                    hosts=None, 
                                    count=1, 
                                    nic='NIC_Basic',
                                    iface_num=0,
                                    cores=2,
                                    ram=8,
                                    disk=10, 
                                    image='default_rocky_8'):  
        from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network
        slice_name = f'test2_{name}_{self.timestamp}'

        
        network_name = f'{site}_net'
        subnet = IPv4Network("192.168.1.0/24")
        available_ips = list(subnet)[1:]  
        target_ip = available_ips[0]
        
        slice = self.fablib.new_slice(name=name)

        node_info = {}
        ifaces = []
        if hosts == None:
            for i in range(count):
                node_name = f"{site}_node{i+1}"

                node= slice.add_node(name=node_name, 
                                           site=site, 
                                           cores=cores,
                                           ram=ram,
                                           disk=disk, image=image)                    
                ifaces.append(node.add_component(model=nic, name='nic1').get_interfaces()[iface_num] )
                node_info[node.get_name()] = { 'ip': available_ips.pop(0) }

        else:
            for host in hosts:
                for i in range(count):
                    node_name = f"{host}_node{i+1}"

                    node = slice.add_node(name=node_name, 
                                          site=site, 
                                          host=host,
                                          cores=cores,
                                          ram=ram,
                                          disk=disk, image=image)
                    ifaces.append(node.add_component(model=nic, name='nic1').get_interfaces()[iface_num])
                    node_info[node.get_name()] = { 'ip': available_ips.pop(0) }


        net1 = slice.add_l2network(name=network_name, interfaces=ifaces)

        self.slice_names.append(name)
        print(f"{node_info}")
                    
        slice_id = slice.submit()
                   
        print(f"{node_info}")

            
        for node in slice.get_nodes(): 
            node_iface = node.get_interface(network_name=network_name) 
            node_addr = node_info[node.get_name()]['ip']
            node_iface.ip_addr_add(addr=node_addr, subnet=subnet)

        threads = {}
        for node in slice.get_nodes(): 
            threads[node.get_name()] = node.execute_thread(f'ping -c 5 {target_ip}')

        for node_name, thread in threads.items():
            print(f'node: {node_name}: ')
            stdout, stderr = thread.result()
            print(f'stdout: {stdout}')
            print(f'stderr: {stderr}')
                
        return slice
    
    def test3_create_nodes_with_components(self, 
                                  name='testing', 
                                  site=None, 
                                  hosts=None, 
                                  count=1, 
                                  cores=2,
                                  ram=8,
                                  disk=10,
                                  components=['NIC_Basic'],image='default_rocky_8'): 
        slice_name = f'test1_{name}_{self.timestamp}'
        
        slice = self.fablib.new_slice(name=slice_name)

        if hosts == None:
            for i in range(count):
                node_name = f"{site}_node{i+1}"

                node = slice.add_node( name=node_name, 
                                site=site,
                                cores=cores,
                                ram=ram,
                                disk=disk, image=image)
                component_num = 1
                for component in components:
                    node.add_component(model=component, name=f'component_{component_num}')
                    component_num = component_num + 1

        else:
            for host in hosts:
                for i in range(count):
                    node_name = f"{host}_node{i+1}"

                    node = slice.add_node(name=node_name, 
                                   site=site, 
                                   host=host, 
                                   cores=cores,
                                   ram=ram,
                                   disk=disk, image=image)
                    component_num = 1
                    for component in components:
                        node.add_component(model=component, name=f'component_{component_num}')
                        component_num = component_num + 1
                
        self.slice_names.append(slice_name)
        
        slice_id = slice.submit()
        
        for node in slice.get_nodes():
            print(f"{node.get_name()}:")
            if image == 'default_ubuntu_20':
                stdout, stderr = node.execute('sudo apt-get install -y -q pciutils && lspci', quiet=False)
            else:
                stdout, stderr = node.execute('sudo yum install -y -q pciutils && lspci', quiet=False)
        
        return slice
                
    def test_execute(self, slice=None, command='echo Hello, FABRIC from node `hostname -s`'):
        
        threads = {}
        for node in slice.get_nodes():
            threads[node] = node.execute_thread(command)

        for node,thread in threads.items():
            print(f'Waiting for {node.get_name()} output:')
            stdout,stderr = thread.result()
            print(f'stdout: {stdout}')
            print(f'stderr: {stderr}')

            

            
            
    def clean_up(self):
        try:
            for name in self.slice_names:
                try:
                    print(f"Deleting slice: {name}")
                    self.fablib.delete_slice(slice_name=name)
                except Exception as e:
                    print(f"Exception: {e}")
            self.slice_names = []
        except Exception as e:
            print(f"Exception: {e}")
            
    @staticmethod
    def clean_up_all():
        try:
            fablib_manager().delete_all()
        except Exception as e:
            print(f"Exception: {e}")



