#!/bin/python3

import json
import time
from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager

import os
import sys

#module_path = os.path.abspath(os.path.join('..'))
#if module_path not in sys.path:
#    sys.path.append(module_path)

#from fablib_local_imports.common_notebook_utils.utils import *
#from fablib_local_imports.common_notebook_utils.fablib_plugin_methods import *
#from fablib_local_imports.common_notebook_utils.fabric_fabnet_slice import *

#from plugins import Plugins
#Plugins.load()

# Define Experiment
class FRRouting_Experiment():

    fablib = None
    slice = None
    slice_id = None
    slice_name = None
    
    router_subnets = []
    local_subnets = []
    all_cidr = None           # 192.168.0.0/16
    all_ip = None             # 192.168.0.0
    all_backward_mask = None  # 0.0.255.255
    all_mask = None           # 255.255.0.0
     
    router_names = []
    router_links = []
    local_networks = []
    
    def __init__(self, 
                 name,
                 output_type='HTML',
                 node_tools=f"fabric_node_tools"):
        print(f"Initializing FRRouting Slice: {name}")
        self.fablib = fablib_manager(output_type=output_type)
        #self.fablib = fablib_manager()
        self.slice_name = name
        self.slice = self.fablib.new_slice(name=self.slice_name)
        self.slice_id = None
        
        self.router_names = []
        self.router_links = []
        self.local_networks = []
        
        # Default IP pools: TODO: allow custom IP pools
        self.all_cidr = '192.168.0.0/16'
        self.all_ip = '192.168.0.0'
        self.all_backward_mask = '0.0.255.255'
        self.all_mask = '255.255.0.0'
        
        self.router_subnets = []
        for i in range(1,33):
            self.router_subnets.append(IPv4Network(f"192.168.{200+i}.0/24"))
            
        self.local_subnets = []
        for i in range(1,33):
            self.local_subnets.append(IPv4Network(f"192.168.{i}.0/24"))

    def list_resources(self):
        self.fablib.get_resources().list()                
        
    def __get_slice(self):
        return self.slice
    
    def __get_slice_name(self):
        return self.slice_name
    
    def __get_slice_id(self):
        return self.slice_id    
    
    def load(self, slice_name=None, path='config'):
        print(f"Loading Slice {slice_name}")
        
        file = open(f"{path}/{self.slice_name}_data.json", "r") 
        config_str = file.read()
        file.close() 
        
        config = json.loads(config_str)
        self.slice_id = config['slice_id']
        self.slice_name = config['slice_name']
        self.router_names = config['router_names']
        self.router_links = config['router_links']
        self.local_networks = config['local_networks']
        
        print(f"self.slice_id: {self.slice_id}")
        print(f"self.slice_name: {self.slice_name}")
        print(f"self.router_names: {self.router_names}")
        print(f"self.router_links: {self.router_links}")
        print(f"self.local_networks: {self.local_networks}")
        
        self.slice = self.fablib.get_slice(name=self.slice_name)
        print(f"{self.slice}")
    
        
        
        

        
    def add_router(self, name=None, site=None, cores=2, ram=8, disk=10, image='default_rocky_8'):
        router = self.slice.add_node(name=name, site=site, cores=cores, ram=ram, disk=disk)
        self.router_names.append(name)
        
        return router
    
    def get_available_router_subnet(self):
        return self.router_subnets.pop(0)
    
    def get_available_local_subnet(self):
        return self.local_subnets.pop(0)
    
        
        
    def add_router_link(self, name=None, router1=None, router2=None, subnet=None, router1_ip=None, router2_ip=None, nic_model='NIC_Basic'):
        
        print(f"add_router_link, name={name}, router1={router1.get_name()}, router2={router2.get_name()}")
        
        # Organize the subnets and IPs
        if subnet:
            route_link_subnet = subnet
        else:
            route_link_subnet = self.get_available_router_subnet() #IPv4Network("192.168.101.0/24")
            
        route_link_available_ips = list(route_link_subnet)[1:]
        
        if not router1_ip:
            router1_ip = route_link_available_ips.pop(0)
        if not router2_ip:
            router2_ip = route_link_available_ips.pop(0)
        

        # Get the routers
        #router1 = self.slice.get_node(name=router1_name)
        #router2 = self.slice.get_node(name=router2_name)
        if nic_model=='NIC_ConnectX_6':
            router1_iface1 = router1.add_component(model='NIC_ConnectX_6', name=f'{name}').get_interfaces()[0]
            router2_iface1 = router2.add_component(model='NIC_ConnectX_6', name=f'{name}').get_interfaces()[0]
        elif nic_model=='NIC_ConnectX_5':
            router1_iface1 = router1.add_component(model='NIC_ConnectX_5', name=f'{name}').get_interfaces()[0]
            router2_iface1 = router2.add_component(model='NIC_ConnectX_5', name=f'{name}').get_interfaces()[0]
        else:
            router1_iface1 = router1.add_component(model='NIC_Basic', name=f'{name}').get_interfaces()[0]
            router2_iface1 = router2.add_component(model='NIC_Basic', name=f'{name}').get_interfaces()[0]
        
            

        #Create Router Links
        router_link = self.slice.add_l2network(name=name, interfaces=[router1_iface1, router2_iface1])
        
        router_link_info = {'name': name,
                            'subnet': str(route_link_subnet),
                            'router1': {'name': router1.get_name(), 'ip': str(router1_ip) },
                            'router2': {'name': router2.get_name(), 'ip': str(router2_ip) }
                            }
        
        self.router_links.append(router_link_info)
        
        self.save_config()
        
        return router_link

    def add_local_network(self, name=None, 
                                       router=None, 
                                       subnet=None, 
                                       router_ip=None, 
                                       node_count=1,
                                       cores=2, ram=8, disk=10, image='default_rocky_8'):
         # Organize the subnets and IPs
        if subnet:
            local_network_subnet = subnet
        else:
            local_network_subnet = self.get_available_local_subnet() #IPv4Network("192.168.101.0/24")
            
        local_network_available_ips = list(local_network_subnet)[1:]
        
        if not router_ip:
            router_ip = local_network_available_ips.pop(0)
              
        ifaces = []
        
        router = self.slice.get_node(name=router.get_name())
        router_iface = router.add_component(model='NIC_Basic', name=f'{name}').get_interfaces()[0]
        
        ifaces.append(router_iface)
            
        site = router.get_site()
        nodes = []
        for i in range(node_count):
            node_name=f'{name}{i+1}'
            node = self.slice.add_node(name=node_name, site=site, cores=cores, ram=ram, disk=disk, image=image)
            node_iface = node.add_component(model='NIC_Basic', name=f'{name}').get_interfaces()[0]
            ifaces.append(node_iface)
            node_ip = local_network_available_ips.pop(0)
            nodes.append({'name': node_name, 'ip': str(node_ip)})
        
        router_local_network = self.slice.add_l2network(name=name, interfaces=ifaces)
 
        local_network_info = {'name': name,
                            'subnet': str(local_network_subnet),
                            'router': {'name': router.get_name(), 'ip': str(router_ip) },
                            'nodes' : nodes 
                            }
        
        self.local_networks.append(local_network_info)
        
        self.save_config()

        
        return router_local_network
    
    def get_all_subnets(self):
        all_subnets = []
        
        for router_link in self.router_links:
            all_subnets.append(IPv4Network(router_link['subnet']))
            
        for local_network in self.local_networks:
            all_subnets.append(IPv4Network(local_network['subnet']))
                               
        return all_subnets
    
    def configure_devs(self):
        
        # Configure router links
        for router_link in self.router_links:
            router_link_name = router_link['name']
            router_link_subnet = IPv4Network(router_link['subnet'])
            
            print(f"Config: {router_link_name}, {router_link_subnet}")
            
            router1 = self.slice.get_node(router_link['router1']['name'])
            router1_ip = IPv4Address(router_link['router1']['ip'])
            router1_iface = router1.get_interface(network_name=router_link_name)
            router1_dev = router1_iface.get_os_interface()
            router1_iface.ip_addr_add(addr=router1_ip, subnet=router_link_subnet)

            router2 = self.slice.get_node(router_link['router2']['name'])
            router2_ip = IPv4Address(router_link['router2']['ip'])
            router2_iface = router2.get_interface(network_name=router_link_name)
            router2_dev = router2_iface.get_os_interface()
            router2_iface.ip_addr_add(addr=router2_ip, subnet=router_link_subnet)

        # Configure local networks
        for local_network in self.local_networks:
            local_network_name = local_network['name']
            local_network_subnet = IPv4Network(local_network['subnet'])
            local_network_router = self.slice.get_node(local_network['router']['name'])
            local_network_router_ip = IPv4Address(local_network['router']['ip'])
            local_network_router_iface = local_network_router.get_interface(network_name=local_network_name)

            local_network_router_iface.ip_addr_add(addr=local_network_router_ip, subnet=local_network_subnet) 
            
            for node_info in local_network['nodes']:
                node_name=node_info['name']
                node_ip=IPv4Address(node_info['ip'])
                node = self.slice.get_node(node_name)
                node_iface = node.get_interface(network_name=local_network_name)
                node_dev = node_iface.get_os_interface()
                node_iface.ip_addr_add(addr=node_ip, subnet=local_network_subnet) 
                
                #for subnet in self.get_all_subnets():
                #    node.ip_route_add(subnet, local_network_router_ip)
                node.ip_route_add(IPv4Network(self.all_cidr), local_network_router_ip)
                    
    def get_routers(self):
        routers = []
        for router_name in self.router_names:  
            routers.append(self.slice.get_node(router_name))
        return routers
    
    def get_edge_nodes(self):
        edge_nodes = []
        
        for node in self.slice.get_nodes():
            if not node.get_name() in self.router_names:
                edge_nodes.append(node)
        return edge_nodes
    
    def get_local_networks(self):        
        return self.local_networks
    
    def get_local_network(self,name): 
        for net in self.get_local_networks():
            if net['name'] == name:
                return net
        
        return None
    
    def get_local_network_names(self): 
        local_network_names = []
        for net in self.get_local_networks():
            local_network_names.append(net['name'])
        
        return local_network_names
    
    def get_router_links(self):        
        return self.router_links

    def get_router_link(self,name): 
        for link in self.get_router_links():
            if link['name'] == name:
                return link
        
        return None
    
    def get_router_link_names(self):
        router_link_names = []
        for link in self.get_router_links():
            router_link_names.append(link['name'])
        
        return router_link_names
          
        
    
    def configure_routers(self, type='ospf'):
        router_names = []
        router_links = []
        local_networks = []
        
        threads = {}
        for router in self.get_routers():            
            print(f"config router: {router.get_name()}")
                        
            router.upload_directory('fabric_node_tools','.')
            router.execute(f'chmod +x fabric_node_tools/*.sh')
            
            #sudo ./node_utils/frr_config.sh  1.2.3.4 1.2.0.0/16 1.2.0.0 0.0.255.255 eth1:1.2.100.100/24 eth2:1.2.101.102/24 1.2.102.102/24
            
            
            zebra_devs = ''
            for iface in router.get_interfaces():
                
                # Test if iface has a network. If not, skip this iface
                try:
                    network_name = iface.get_network().get_name()
                except:
                    continue
                
                if iface.get_network().get_name() in self.get_local_network_names():
                    local_network_name = iface.get_network().get_name()
                    local_network = self.get_local_network(local_network_name)
                    router_local_ip = iface.get_ip_addr()
                    zebra_devs=f"{zebra_devs} {iface.get_os_interface()}:{local_network['subnet']}"
                    
                else:
                    router_link_name = iface.get_network().get_name()
                    router_link = self.get_router_link(router_link_name)
                    zebra_devs=f"{zebra_devs} {iface.get_os_interface()}:{router_link['subnet']}"
                    
            
            command= 'sudo ./fabric_node_tools/frr_config.sh {} {} {} {} {}'.format(router_local_ip,
                                                                              self.all_cidr,
                                                                              self.all_ip,
                                                                              self.all_backward_mask,
                                                                              zebra_devs)
            #command=f'{command} {router_local_ip}'
            #command=f'{command} {self.all_cidr}'
            #command=f'{command} {self.all_ip}'
            #command=f'{command} {self.all_backward_mask}'
            #for all devs:   command=f'{command} dev:subnet_cidr'
            print(f"router: {router.get_name()}, command: {command}")
            
            threads[router] = router.execute_thread(command) 
            
        for router,thread in threads.items():
            print(f"waiting for {router.get_name()} config")
            stdout, stderr = thread.result()
        
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")

       
    def save_config(self, path='config'):
    
        config = { 'slice_id': self.slice_id,
                   'slice_name' :  self.slice_name,
                    'router_names' : self.router_names,
                    'router_links' : self.router_links,
                    'local_networks' : self.local_networks }
 
    
        file = open(f"{path}/{self.slice_name}_data.json", "w") 
        n = file.write(json.dumps(config))
        file.close() 
        
    def save_fim_topology(self, path='config'):
        self.slice.save(f"{path}/{self.slice_name}_topology.json")

    def configure_local_nodes(self):
        pass
            
    def submit(self):
        self.slice_id = self.slice.submit(wait=False)
        
        self.save_config()
        
    def wait(self):
        self.slice.wait_ssh(progress=True)
        
    def wait_jupyter(self):
        self.slice.wait_jupyter()
        
    def post_boot_config(self):
        self.slice.post_boot_config()
        
   

    def delete(self,name=None):
        fablib = fablib_manager()
        fablib.delete_slice(name)

