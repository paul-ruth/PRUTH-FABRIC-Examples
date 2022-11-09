#!/bin/python3

import json
import time
from ipaddress import ip_address, IPv4Address, IPv6Address, IPv4Network, IPv6Network

from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager


import os
import sys

module_path = os.path.abspath(os.path.join(f"{os.environ['HOME']}/work/PRUTH-FABRIC-Examples/fablib_local"))
if module_path not in sys.path:
    sys.path.append(module_path)
#from fablib_custom.fablib_custom import *




from chameleon_utils.chameleon_stitching import *
from chameleon_utils.chameleon_servers import *

from fablib_common_utils.utils import *

from performance_testing.iperf3 import *



import os
import sys

import ipycytoscape as cy
from IPython.display import display
from ipywidgets import Output
import ipywidgets as widgets
from ipywidgets import HTML, Layout


# module_path = os.path.abspath(os.path.join('..'))
# if module_path not in sys.path:
#    sys.path.append(module_path)

from chameleon_utils.chameleon_stitching import *
from chameleon_utils.chameleon_servers import *
from fablib_common_utils.utils import *

from concurrent.futures import ThreadPoolExecutor


# from fablib_local_imports.common_notebook_utils.utils import *
# from fablib_local_imports.common_notebook_utils.fablib_plugin_methods import *
# from fablib_local_imports.common_notebook_utils.fabric_fabnet_slice import *

# from plugins import Plugins
# Plugins.load()

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
    
    nodes = []
    
    def __init__(self, 
                 name,
                 output=None,
                 node_tools=f"{os.environ['HOME']}/work/PRUTH-FABRIC-Examples/fabric_node_tools",
                 #node_tools=f"fabric_node_tools",
                 verbose=False):
        if verbose:
            print(f"Initializing FRRouting Slice: {name}")
            
        self.fablib = fablib_manager(output=output)
        #self.fablib = fablib_manager()
        self.slice_name = name
        self.slice = self.fablib.new_slice(name=self.slice_name)
        self.slice_id = None
        
        self.router_names = []
        self.router_links = []
        self.local_networks = []
        
        self.nodes = []
        
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
            
        self.thread_pool_executor = ThreadPoolExecutor(10)
        
    
    def configure(self, frr_sites, frr_links):
        import traceback
        try:
            self.node_logs = {}
            
            # Add routers
            routers = {}
            for name, data in frr_sites.items():
                routers[name] = self.add_router(name=f'{name}_Router', site=data['site'], cores=32, ram=128, disk=10)

            # Add links between routers
            links = {}
            for name, data in frr_links.items():
                router_a_name, router_b_name = data
                router_a = routers[router_a_name]
                router_b = routers[router_b_name]

                routers[name] = self.add_router_link(name=name, router1=router_a, router2=router_b, nic_model='NIC_Basic')

            # Add local networks and nodes
            for name, data in frr_sites.items():
                if data['facility'] == 'FABRIC':
                    self.add_local_network(name=f'{name}',           #name=f'{name}_local_net', 
                                           router=routers[name], 
                                           node_count=data['node_count'], 
                                           cores=8, ram=32, disk=10)
                elif data['facility'] == 'CHI@UC':
                    self.add_chameleon_local_network(name=f'{name}',  #name=f'{name}_local_net', 
                                                     router=routers[name], 
                                                     node_count=data['node_count'], 
                                                     verbose=True)
                else:
                    print(f"Unknown facility")
            
        except Exception as e:
            print(f"Slice Fail: {e}")
            traceback.print_exc()
        
    def deploy(self):
        print('Submit FABRIC Slice...')
        self.submit()
        print('Deploy Node Tools...')
        self.execute_on_all_edge_nodes(f'rm -rf fabric_node_tools')
        self.upload_directory_to_all_edge_nodes('fabric_node_tools','.')
        self.execute_on_all_edge_nodes(f'chmod +x fabric_node_tools/*.sh')
        print('Configure Node Devices...')
        self.configure_devs()
        print('Configure Routers...')
        self.configure_routers()
        print('Tune Network Devices...')
        command = f'sudo yum install -y -q iperf3 iproute-tc && sudo ./fabric_node_tools/host_tune_redhat.sh'
        self.execute_on_all_edge_nodes(f'{command}')
        print('Done')

        
    
            
    def get_ssh_thread_pool_executor(self):
        return self.thread_pool_executor

    def list_sites(self):
        self.fablib.list_sites()               
        
    def __get_slice(self):
        return self.slice
    
    def __get_slice_name(self):
        return self.slice_name
    
    def __get_slice_id(self):
        return self.slice_id    
    
    def load(self, slice_name=None, path='config', verbose=False):
        #print(f"Loading Slice")# {slice_name}")
        
        file = open(f"{path}/{self.slice_name}_data.json", "r") 
        config_str = file.read()
        file.close() 
        
        config = json.loads(config_str)
        self.slice_id = config['slice_id']
        self.slice_name = config['slice_name']
        self.router_names = config['router_names']
        self.router_links = config['router_links']
        self.local_networks = config['local_networks']
        self.nodes = config['nodes']
        
        self.slice = self.fablib.get_slice(name=self.slice_name)

        self.update_nodes()
        
        if verbose:
            print(f"self.slice_id: {self.slice_id}")
            print(f"self.slice_name: {self.slice_name}")
            print(f"self.router_names: {self.router_names}")
            print(f"self.router_links: {self.router_links}")
            print(f"self.local_networks: {self.local_networks}")
            print(f"self.nodes: {self.nodes}")
            print(f"{self.slice}")
            
            
    
        
        
    def update_nodes(self):
        for node in self.nodes:
            if node['facility'] == 'FABRIC':
                fnode = self.slice.get_node(node['name'])
                node['management_ip'] = str(fnode.get_management_ip())

        
    def add_router(self, name=None, site=None, cores=2, ram=8, disk=10, image='default_rocky_8'):
        
        #if site == 'STAR':
        #    host_num = 5
        #else:
        #    host_num = int(self.fablib.get_resources().get_cpu_capacity(site)/2)
        #
        #host = f"{site.lower()}-w{host_num}.fabric-testbed.net"
        
        self.node_logs[name] = f'{name}.log'

        
        router = self.slice.add_node(name=name, site=site, cores=cores, ram=ram, disk=disk) #, host=host)
        self.router_names.append(name)
        
        return router
    
    def get_available_router_subnet(self):
        return self.router_subnets.pop(0)
    
    def get_available_local_subnet(self):
        return self.local_subnets.pop(0)
    
        
        
    def add_router_link(self, 
                        name=None, 
                        router1=None, 
                        router2=None, 
                        subnet=None, 
                        router1_ip=None, 
                        router2_ip=None, 
                        nic_model='NIC_Basic',
                        verbose=False):
        
        if verbose:
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

    def add_chameleon_local_network(self, name=None, router=None, subnet=None, 
                                       router_ip=None, node_count=0, verbose=False):
         # Organize the subnets and IPs
        if subnet:
            local_network_subnet = subnet
        else:
            local_network_subnet = self.get_available_local_subnet() #IPv4Network("192.168.101.0/24")
            
        local_network_available_ips = list(local_network_subnet)[1:]
        
        if not router_ip:
            router_ip = local_network_available_ips.pop(0)
            
        
        # Create Chameleon leases
        time_stamp = datetime.now(tz=tz.tzutc()).strftime('%Y%m%d%H%M')

        network_lease_name = f"pruth_{time_stamp}_{name}_stitched_network"
        server_lease_name = f"pruth_{time_stamp}_{name}_stitched_servers"
        #server_lease_name = f"{name}"
        
        ifaces = []
        
        router = self.slice.get_node(name=router.get_name())
        router_iface = router.add_component(model='NIC_ConnectX_6', name=f'{name}').get_interfaces()[0]
        #router_iface = router.add_component(model='NIC_Basic', name=f'{name}').get_interfaces()[0]
        
        ifaces.append(router_iface)
            
        site = router.get_site()
        
        #Create Chameleon network
        fabric_net_lease = create_chameleon_stitched_network(name=network_lease_name)
        
        chameleon_network = get_chameleon_network(chameleon_network_name=network_lease_name, lease=fabric_net_lease)
        stitch_vlan = get_chameleon_network_vlan(chameleon_network=chameleon_network)
        chameleon_network_id = get_chameleon_network_id(chameleon_network=chameleon_network)
        
        if verbose:
            print(f"network_lease_name: {network_lease_name}")
            print(f"stitch_vlan: {stitch_vlan}")
            print(f"chameleon_network_id: {chameleon_network_id}")
        
        
        #chameleon_server_name = network_lease_name
        chameleon_network_name = network_lease_name
        chameleon_subnet_name = network_lease_name
        chameleon_router_name = network_lease_name
        
        #Network Config
        #subnet = IPv4Network("192.168.100.0/24")
        
        chameleon_gateway_ip=local_network_available_ips[10]
        router_ip=local_network_available_ips[11]
        chameleon_allocation_pool_start=local_network_available_ips[12]
        chameleon_allocation_pool_end=local_network_available_ips[43]    
        local_network_available_ips = local_network_available_ips[44:] 
        
        if verbose:
            print(f"chameleon_gateway_ip: {chameleon_gateway_ip}")
            print(f"router_ip: {router_ip}")
            print(f"chameleon_allocation_pool_start: {chameleon_allocation_pool_start}")
            print(f"chameleon_allocation_pool_end: {chameleon_allocation_pool_end}")
                
        configure_chameleon_network(chameleon_network_name=network_lease_name,
                                chameleon_network=chameleon_network, 
                                subnet=local_network_subnet, 
                                chameleon_allocation_pool_start=chameleon_allocation_pool_start, 
                                chameleon_allocation_pool_end=chameleon_allocation_pool_end,
                                chameleon_gateway_ip=chameleon_gateway_ip,
                                fabric_gateway=router_ip,
                                add_chameleon_router=True,
                                fabric_route_subnet="192.168.0.0/16")    
        
        
        fabric_facility_port = self.slice.add_facility_port(name='Chameleon-StarLight', site='STAR', vlan=str(stitch_vlan))
        fabric_facility_port_iface = fabric_facility_port.get_interfaces()[0]

        fabric_net = self.slice.add_l2network(name=f'{name}', 
                                              interfaces=[router_iface,fabric_facility_port_iface]) 
    
        nodes = []
        if node_count > 0:
            server_lease = create_chameleon_server_lease(name=server_lease_name, count=node_count) 
            
            for i in range(1,node_count+1):
                #node_name = f"{server_lease_name}{i}"
                node_name = f"{name}{i}"
                create_chameleon_servers(name=node_name, 
                                  count=1, 
                                  #node_type=default_chameleon_node_type,
                                  #image_name=default_chameleon_image_name,
                                  key_name='my_chameleon_key',
                                  network_name=chameleon_network_name,
                                  lease=server_lease)
                
                server_id = chi.server.get_server_id(node_name)
                fixed_ip = chi.server.get_server(server_id).interface_list()[0].to_dict()["fixed_ips"][0]["ip_address"]
                
                floating_ip=get_free_floating_ip()
                floating_ip_address = floating_ip['floating_ip_address']
    
                associate_floating_ip(server_id, floating_ip_address=floating_ip_address)
                
                self.nodes.append( { 'name': node_name,
                                     'facility': 'Chameleon',
                                     'site': 'CHI@UC',
                                     'management_ip': str(floating_ip_address),
                                     'data_plane_ip': str(fixed_ip),
                                     'local_net': str(name),
                                   } 
                                 )
                
                

         
        local_network_info = {  'name': name,
                                'router_site': site,
                                'node_site': 'Chameleon@UC',                                
                                'subnet': str(local_network_subnet),
                                'router': {'name': router.get_name(), 'ip': str(router_ip) },
                                'nodes' : nodes 
                                }
        
        self.local_networks.append(local_network_info)
        
        self.save_config()
            
        
    
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
            self.node_logs[node_name] = f'{name}.log'

            
            node = self.slice.add_node(name=node_name, site=site, cores=cores, ram=ram, disk=disk, image=image)
            node_iface = node.add_component(model='NIC_Basic', name=f'{name}').get_interfaces()[0]
            ifaces.append(node_iface)
            node_ip = local_network_available_ips.pop(0)
            nodes.append({'name': node_name, 'ip': str(node_ip)})
            
            self.nodes.append( { 'name': node_name,
                                 'facility': 'FABRIC',
                                 'site': site,
                                 'management_ip': None,
                                 'data_plane_ip': str(node_ip),
                                 'local_net': str(name),
                                   } 
                                 )
        
        router_local_network = self.slice.add_l2network(name=name, interfaces=ifaces)
 
        local_network_info = {  'name': name,
                                'router_site': site,
                                'node_site': site,
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
    
    def configure_devs(self, verbose=False):
        
        
        
        # Configure router links
        for router_link in self.router_links:
            router_link_name = router_link['name']
            router_link_subnet = IPv4Network(router_link['subnet'])
            
            if verbose:
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
            
            if local_network['node_site'] == 'Chameleon@UC':
                continue
            
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
    
    
    def upload_directory(self, node, directory, verbose=False):
        #if verbose:
        #    print(json.dumps(node, indent=4))

        if node['facility'] == 'FABRIC':
            fnode = self.slice.get_node(node['name'])
            rtn_val = fnode.upload_directory(directory,'.')
            #if verbose:
            #    print(f"rtn_val: {rtn_val}")

        elif node['facility'] == 'Chameleon':        
            rtn_val = upload_directory(directory,'.', 
                    username='cc', 
                    ip_addr= node['management_ip'],
                    private_key_file='/home/fabric/work/fablib_local_private_config/my_chameleon_key') 
            #if verbose:
            #    print(f"rtn_val: {rtn_val}")
        else:
            pass
            #if verbose:
            #    print('Unkown facility')
    
    def upload_file(self, node, local_file=None, remote_file='.', verbose=False):
        if verbose:
                print(json.dumps(node, indent=4))

        if node['facility'] == 'FABRIC':

            fnode = self.slice.get_node(node['name'])
            rtn_val = fnode.upload_file(local_file, remote_file)
            if verbose:
                print(f"rtn_val: {rtn_val}")

        elif node['facility'] == 'Chameleon':        
            rtn_val = upload_file(local_file, remote_file, 
                    username='cc', 
                    ip_addr= node['management_ip'],
                    private_key_file='/home/fabric/work/fablib_local_private_config/my_chameleon_key') 
            if verbose:
                print(f"rtn_val: {rtn_val}")
        else:
            if verbose:
                print('Unkown facility')
                
    def download_file(self, node, local_file=None, remote_file=None, verbose=False):
        if verbose:
                print(json.dumps(node, indent=4))

        if node['facility'] == 'FABRIC':

            fnode = self.slice.get_node(node['name'])
            rtn_val = fnode.download_file(local_file, remote_file)
            if verbose:
                print(f"rtn_val: {rtn_val}")

        elif node['facility'] == 'Chameleon':        
            rtn_val = download_file(local_file, remote_file, 
                    username='cc', 
                    ip_addr= node['management_ip'],
                    private_key_file='/home/fabric/work/fablib_local_private_config/my_chameleon_key') 
            if verbose:
                print(f"rtn_val: {rtn_val}")
        else:
            if verbose:
                print('Unkown facility')
        
    
    def upload_directory_to_all_edge_nodes(self, directory, verbose=False):
        for node in self.nodes:
            rtn_val = self.upload_directory(node,directory,verbose=False)
    
    
    def execute(self, node, command, verbose=False):
        stdout = None
        stderr = None
        
        if verbose:
                print(json.dumps(node, indent=4))

        if node['facility'] == 'FABRIC':

            fnode = self.slice.get_node(node['name'])
            stdout, stderr = fnode.execute(command)
            if verbose:
                print(f"stdout: {stdout}")
                print(f"stderr: {stderr}")

        elif node['facility'] == 'Chameleon':        
            stdout, stderr = execute(command, 
                    username='cc', 
                    ip_addr= node['management_ip'],
                    private_key_file='/home/fabric/work/fablib_local_private_config/my_chameleon_key') 
            if verbose:
                print(f"stdout: {stdout}")
                print(f"stderr: {stderr}")
        else:
            if verbose:
                print('Unkown facility')
                
        return stdout,stderr

    def execute_thread(self, node, command, verbose=False): 
         return self.get_ssh_thread_pool_executor().submit(self.execute,
                                                            node,
                                                            command,
                                                            verbose=False)
                                                                                 
    
    def execute_on_all_edge_nodes(self, command, verbose=False):
        for node in self.nodes:
            self.execute(node,command,verbose=verbose)
            
            
    def get_node(self, name):
        for node in self.nodes:
            if node['name'] == name:
                return node
            
        return None
                
            
    def get_edge_nodes(self):
        edge_nodes = []
        
        for node in self.nodes:
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
          
        
    
    def configure_routers(self, type='ospf', verbose=False):
        router_names = []
        router_links = []
        local_networks = []
        
        threads = {}
        for router in self.get_routers():
            if verbose:
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
            if verbose:
                print(f"router: {router.get_name()}, command: {command}")
            
            threads[router] = router.execute_thread(command) 
            
        for router,thread in threads.items():
            if verbose:
                print(f"waiting for {router.get_name()} config")
            stdout, stderr = thread.result()
        
            if verbose:
                print(f"stdout: {stdout}")
                print(f"stderr: {stderr}")

       
    def save_config(self, path='config'):
    
        config = { 'slice_id': self.slice_id,
                   'slice_name' :  self.slice_name,
                    'router_names' : self.router_names,
                    'router_links' : self.router_links,
                    'local_networks' : self.local_networks,
                     'nodes': self.nodes}
 
    
        file = open(f"{path}/{self.slice_name}_data.json", "w") 
        n = file.write(json.dumps(config))
        file.close() 
        
    def save_fim_topology(self, path='config'):
        self.slice.save(f"{path}/{self.slice_name}_topology.json")

    def configure_local_nodes(self):
        pass
            
    def submit(self):
        #self.slice_id = self.slice.submit(wait=False)
        self.slice_id = self.slice.submit(wait_timeout=10000)
        
        self.save_config()
        
    def wait(self):
        self.slice.wait_ssh(progress=True)
        
    def wait_jupyter(self, timeout=600, interval=10):
        self.slice.wait_jupyter(timeout=timeout, interval=interval)
        
    def post_boot_config(self):
        self.slice.post_boot_config()
        
   

    def delete(self,name=None):
        fablib = fablib_manager()
        fablib.delete_slice(name)
        
    def iperf3_process_output(self,output_dir='output', verbose=False):

        files = os.listdir(output_dir)   

        run_suffix = '_client_summary_output' 
        runs = {}                
        for file in files:
            if file.endswith(run_suffix):
                run_name = file.removesuffix(run_suffix)

                #open text file in read mode
                #print(f"file: {output_dir}/{file}")
                f = open(f'{output_dir}/{file}', "r")
                run_output = f.read()
                f.close()

                runs[run_name] =  json.loads(run_output)


        #print(f"{runs}")
        table = []
        for run_name,streams in runs.items():

            #print(f"{run_name}")

            run_bandwidth = 0.0
            run_retransmits = 0
            run_max_rtt = 0
            run_min_rtt = -1
            run_mean_rtt = 0
            run_mtu = 0

            for stream in streams:

                #for k1,v1 in stream.items():
                #    print(f"key: {k1}")

                run_mtu = stream['intervals'][0]['streams'][0]['pmtu']

                stream_port = stream['start']['connecting_to']['port']
                stream_bandwidth =  stream['end']['sum_received']['bits_per_second']*0.000000001
                stream_retransmits =  stream['end']['sum_sent']['retransmits']
                stream_max_rtt =  stream['end']['streams'][0]['sender']['max_rtt']*0.001
                stream_min_rtt =  stream['end']['streams'][0]['sender']['min_rtt']*0.001
                stream_mean_rtt =  stream['end']['streams'][0]['sender']['mean_rtt']*0.001
                stream_host_total = stream['end']['cpu_utilization_percent']['host_total']   
                stream_host_user = stream['end']['cpu_utilization_percent']['host_user']
                stream_host_system = stream['end']['cpu_utilization_percent']['host_system']
                stream_remote_total = stream['end']['cpu_utilization_percent']['remote_total']
                stream_remote_user = stream['end']['cpu_utilization_percent']['remote_user']
                stream_remote_system = stream['end']['cpu_utilization_percent']['remote_system']
                stream_sender_tcp_congestion = stream['end']['sender_tcp_congestion']
                stream_receiver_tcp_congestion = stream['end']['receiver_tcp_congestion']

                #print(f"Stream: {stream_port}. bw = {stream_bandwidth}")
                run_bandwidth += stream_bandwidth
                run_retransmits += stream_retransmits

                if stream_max_rtt > run_max_rtt:
                    run_max_rtt = stream_max_rtt

                if stream_min_rtt < run_min_rtt or run_min_rtt == -1:
                    run_min_rtt = stream_min_rtt

                run_mean_rtt += stream_mean_rtt

            run_mean_rtt = run_mean_rtt / len(streams)

            
            timestamp,source,target = run_name.split('__')
            #run = len(table)


            table.append( [    timestamp, source, target,
                                len(streams),
                                run_mtu,
                                f'{run_bandwidth:.3f}',
                                f'{run_max_rtt:.2f}',
                                f'{run_min_rtt:.2f}',
                                f'{run_mean_rtt:.2f}',
                                run_retransmits,
                                ] )
            #if verbose:
                #print(f"{run_name}: pmtu: {run_mtu}, bw: {run_bandwidth:.3f} Gbps, rtt ms (max/min/mean): {run_max_rtt:.2f}/{run_min_rtt:.2f}/{run_mean_rtt:.2f} ms, retransmits: {run_retransmits}")
        headers=["Timestamp", "Source", "Target", "P", "pmtu",  "bw", "rtt_max", "rtt_min", "rtt_mean", "retransmits" ]
        printable_table = self.create_table_local(table, title=f'iPerf3 Results', properties={'text-align': 'left'}, headers=headers, index='Timestamp')
        display(printable_table)

        
    def iperf3_run(self, 
                   source_node=None, 
                   target_node=None, 
                   w=None, P=1, t=60, i=10, O=None, verbose=True):
        from IPython.display import clear_output
        from concurrent.futures import ThreadPoolExecutor
        
        print(f"Running: {source_node['name']} to {target_node['name']} (w:{w}, P:{P}, t:{t}, O:{O}, i:{i}) ...")
        
        thread_pool_executor = ThreadPoolExecutor(10)
        
        target_ip=target_node['data_plane_ip']
        
        #run_name=f"{source_node['name']}_{target_node['name']}_{datetime.now(tz=tz.tzutc()).strftime('%Y%m%d%H%M')}"
        run_name=f"{datetime.now(tz=tz.tzutc()).strftime('%Y%m%d%H%M')}__{source_node['name']}__{target_node['name']}"
        
        #target_thread = target_node.execute_thread(f'./fabric_node_tools/iperf3_server.sh {run_name} {P}')
        
        
        command = f'./fabric_node_tools/iperf3_server.sh {run_name} {P}'
        #command = f'iperf -J -t {t} -i {i} -c {target_ip} -P {P}'
        #if verbose:
            #print(f"Running: {command}")
        
        target_thread = self.execute_thread(target_node,command, verbose=False) 

        # Make sure the target is running before the source starts
        time.sleep(10)

        net_name = f"{target_node['site']}_net"

        retry = 3
        while retry > 0:
            command = f'./fabric_node_tools/iperf3_client.sh {run_name} {target_ip} {P} -t {t} -i {i}'
            #command = f'iperf -J -t {t} -i {i} -c {target_ip} -P {P}'
            if O != None:
                command = f'{command} -O {O}'

            if w != None:
                command = f'{command} -w {w}'
            
            if verbose:
                print(f"{command}")

            source_thread = self.execute_thread(source_node, command, verbose=False)

            if verbose:
                print(f"source_thread: {source_thread}")
            
            source_stdout, source_stderr = source_thread.result()

            if verbose:
                print(f"source_stdout: {source_stdout}")
                print(f"source_stderr: {source_stderr}")


            #if 'error' in json.loads(source_stdout).keys():
            #    print(f"{source_node.get_name()} -> {target_node.get_name()} {target_ip}: error: {json.loads(source_stdout)['error']}")
            #    retry = retry - 1
            #    time.sleep(5)
            #    continue

            break



        #print(f"source_stderr: {source_stderr}")

        # Start target thread
        target_stdout, target_stderr = target_thread.result()
        if verbose:
            print(f"target_stdout: {target_stdout}")
            print(f"target_stderr: {target_stderr}")

        time.sleep(10)

        self.download_file(source_node, f'./output/{run_name}_client_summary_output',f'{run_name}_client_summary_output')
        self.download_file(target_node, f'./output/{run_name}_server_summary_output',f'{run_name}_server_summary_output')

        #source_node.download_file(f'./output/{run_name}_client_summary_output',f'{run_name}_client_summary_output')
        #target_node.download_file(f'./output/{run_name}_server_summary_output',f'{run_name}_server_summary_output')
        
        #if verbose:
        print(f"Done!")
        
    ######## Cytoscape Methods #########
    
    
    # FABRIC design elements https://fabric-testbed.net/branding/style/
    FABRIC_PRIMARY = '#27aae1'
    FABRIC_PRIMARY_LIGHT = '#cde4ef'
    FABRIC_PRIMARY_DARK = '#078ac1'
    FABRIC_SECONDARY = '#f26522'
    FABRIC_SECONDARY_LIGHT = '#ff8542'
    FABRIC_SECONDARY_DARK = '#d24502'
    FABRIC_BLACK = '#231f20'
    FABRIC_DARK = '#433f40'
    FABRIC_GREY = '#666677'
    FABRIC_LIGHT = '#f3f3f9'
    FABRIC_WHITE = '#ffffff'
    FABRIC_LOGO = "fabric_logo.png"

    def display_init(self):
        """
        Constructor
        :return:
        """
        #super().__init__()
    
        self.out = Output()

        

    def display_set_style(self):

        self.cytoscapeobj.set_style([
                        {
                        'selector': 'node',
                        'css': {
                            'content': 'data(name)',
                            'color': 'white',
                            'text-outline-width': 2,
                            'text-outline-color': self.FABRIC_DARK,
                            'background-color': self.FABRIC_GREY,
                            'font-weight': 400,
                            'text-halign': 'right',
                            'text-valign': 'bottom',
                            'font-size': 12,
                            }
                        },
                        {
                        'selector': "node.router",
                        'css': {
                            'text-outline-color': self.FABRIC_SECONDARY_DARK,
                            'background-color': self.FABRIC_SECONDARY,
                            'shape': 'roundrectangle',
                            }
                        },
                        {
                        'selector': "node.local_net",
                        'css': {
                            'text-outline-color': self.FABRIC_DARK,
                            'background-color': self.FABRIC_GREY,
                            'shape': 'triangle'
                            }
                        },
                        {
                        'selector': 'node.edge_node',
                        'css': {
                            'text-outline-color': self.FABRIC_PRIMARY_DARK,
                            'background-color': self.FABRIC_PRIMARY,
                            'shape': 'roundrectangle',
                            }
                        },
                        {
                        'selector': "node.selected",
                        'css': {
                            #'background-color': self.FABRIC_PRIMARY_DARK,
                            #'background-blacken': '0.2',
                            'border-color': self.FABRIC_BLACK,
                            'border-width': 6,
                            'border-style': 'solid',
                            'text-outline-color': self.FABRIC_BLACK,
                            #'background-opacity': 0.5
                            #'shape': 'round-diamond',
                            }
                        },
                        
                        #{
                        #  'selector': ":selected",
                        #  'css': {
                        #    "background-color": "black",
                        #    "line-color": "black",
                        #    "target-arrow-color": "black",
                        #    "source-arrow-color": "black"
                        #  }
                        #}
                        
                        ])


    def build_data(self, verbose=False):
        cy_nodes = self.data['nodes']
        cy_edges = self.data['edges']

        # Build Site
        #print(f"{self.router_names}")

        for router_name in self.router_names:
            router = self.slice.get_node(name=router_name) 
            if verbose:
                print(f"router_name: {router_name}, index: {self.router_names.index(router_name)}")
            #cy_nodes.append({ 'classes': 'router', 'data': { 'id': str(self.router_names.index(router_name)), 'name': router_name, 'href': 'http://cytoscape.org' }, 'position': {}})
            cy_nodes.append({ 'classes': 'router unselected', 'data': { 'id': router_name, 'name': router_name, 'href': 'http://cytoscape.org' }, 'position': {}})

            
        #print(f"{self.router_links}")
        for link in self.router_links:
            router1_name = link['router1']['name']
            router2_name = link['router2']['name']
        
            cy_edges.append({'data': { 'source': router1_name, 'target': router2_name } , 'position': {} })
            
        
        for local_network in self.local_networks:
            #print(f"local_network: {local_network}")
            cy_nodes.append({ 'classes': 'local_net', 'data': { 'id': local_network['name'], 'name': local_network['subnet'], 'href': 'http://cytoscape.org' }, 'position': {}})
            cy_edges.append({'data': { 'source': local_network['router']['name'], 'target': local_network['name'] } , 'position': {} })
        
        
        for node in self.nodes:
            #print(f"node: {node}")
            cy_nodes.append({ 'classes': 'edge_node unselected', 'data': { 'id': node['name'], 'name': node['name'], 'href': 'http://cytoscape.org' }, 'position': {}})
            cy_edges.append({'data': { 'source': node['local_net'], 'target': node['name'] } , 'position': {} })
        

        self.cytoscapeobj.graph.add_graph_from_json(self.data)
        
        #print(f"building cytoscape_node_map")
        self.cytoscape_node_map = {}
        for node in self.cytoscapeobj.graph.nodes:
            #print(node.data['id'])
            self.cytoscape_node_map[node.data['id']] = node

        #print(f"self.cytoscape_node_map: {self.cytoscape_node_map}")
        
       
        return 
    
    def setup_interaction(self):
        #out = Output()
        self.cytoscapeobj.on('node', 'click', self.on_click)
        #self.cytoscapeobj.on('node', 'mouseover', self.on_mouseover)
        
        self.run_btn.on_click(callback=self.run_btn_callback)
        self.clear_btn.on_click(callback=self.clear_btn_callback)
        self.path_btn.on_click(callback=self.path_btn_callback)

        
    def redraw_node_info(self):
        #with self.out:
        #    print('redraw_node_info: ')
        
        #with self.out: print(f"self.selected_node1: {self.selected_node1}")
        #with self.out: print(f"self.selected_node2: {self.selected_node2}")

        if self.selected_node1:                     
            node1 = self.get_node(self.selected_node1.data['name'])
            
            #with self.out: print(f"node1: {node1}")
            
            self.node1_info['name'].value = node1['name']
            self.node1_info['facility'].value = node1['facility']
            self.node1_info['site'].value = node1['site']
            self.node1_info['dataplane_ip'].value = node1['data_plane_ip']
            self.node1_info['management_ip'].value = str(node1['management_ip'])

            #with self.out: print(f"node1_info: {self.node1_info}")
            
            
            if node1['facility'] == 'FABRIC':
                fnode = self.slice.get_node(node1['name'])   
                self.node1_info['type'].value = f"VM (cores:{fnode.get_cores()}, ram: {fnode.get_ram()}, disk: {fnode.get_disk()})"
            elif node1['facility'] == 'Chameleon': 
                self.node1_info['type'].value = 'Baremetal'
            else:
                self.node1_info['type'].value = 'unknown'
        else:
            self.node1_info['name'].value = ''
            self.node1_info['type'].value = ''
            self.node1_info['site'].value = ''
            self.node1_info['facility'].value = ''            
            self.node1_info['dataplane_ip'].value = ''            
            self.node1_info['management_ip'].value = ''            
            
            
        if self.selected_node2:
            node2 = self.get_node(self.selected_node2.data['name'])
            
            #with self.out: print(f"node2: {node2}")
            
            self.node2_info['name'].value = node2['name']
            self.node2_info['facility'].value = node2['facility']
            self.node2_info['site'].value = node2['site']
            self.node2_info['dataplane_ip'].value = node2['data_plane_ip']
            self.node2_info['management_ip'].value = str(node2['management_ip'])

            #with self.out: print(f"node2_info: {self.node2_info}")
            
            
            if node2['facility'] == 'FABRIC':
                fnode = self.slice.get_node(node2['name'])   
                self.node2_info['type'].value = f"VM (cores:{fnode.get_cores()}, ram: {fnode.get_ram()}, disk: {fnode.get_disk()})"
            elif node2['facility'] == 'Chameleon': 
                self.node2_info['type'].value = 'Baremetal'
            else:
                self.node2_info['type'].value = 'unknown'
        else:
            self.node2_info['name'].value = ''
            self.node2_info['type'].value = ''
            self.node2_info['site'].value = ''
            self.node2_info['facility'].value = ''            
            self.node2_info['dataplane_ip'].value = ''            
            self.node2_info['management_ip'].value = ''  
            
            
        from IPython.display import clear_output
        from performance_testing.iperf3 import iperf3_process_output
        with self.out: 
            clear_output(wait=True)
            self.iperf3_process_output(verbose=False)
            #iperf3_process_output(verbose=True)

            
       
            
               
    def on_click(self, event):
        #with self.out:
            #print('\nclick: {}'.format(str(event)))
            #for node in self.cytoscapeobj.graph.nodes:
            #    print(node.data['name'])
            
        #with self.out: print(f'self.cytoscape_node_map: {self.cytoscape_node_map}')
        
        try:
            curr_node = self.cytoscape_node_map[str(event['data']['id'])]
            #curr_node = self.cytoscapeobj.graph.nodes[int(event['data']['id'])]
        except Exception as e:
            with self.out:
                print(e)
        
        #with self.out: print(f'here0')
         
        current_node_classes = curr_node.classes
        
        #with self.out: print(f'here0.1')
        classes = set(curr_node.classes.split(" "))
        #with self.out: print(f'here0.2')
        if 'selected' in classes:
            with self.out: print(f'returning, already selected: current_node_classes: {current_node_classes}')
            return
            
        #with self.out:
        #    print(f'current_node_classes: {current_node_classes}')
                
        if self.selected_node1 == None:
            #with self.out: print(f'setting: selected_node1: {current_node_classes}')
            self.selected_node1 = curr_node
        elif self.selected_node2 == None:
            #with self.out: print(f'setting: selected_node2: {current_node_classes}')
            self.selected_node2 = curr_node
        else:
            pass
            #with self.out: print(f'return without setting: selected_node: {current_node_classes}')

            return
        
        for node in self.cytoscapeobj.graph.nodes:
            classes = set(node.classes.split(" "))
            #print(f"classes: {classes}")
            if "selected" in classes:
                classes.remove("selected")
            classes.add("unselected")
            node.classes = " ".join(classes)
     
        #with self.out: print(f'here1')
    
        if self.selected_node1: 
            classes = set(self.selected_node1.classes.split(" "))
            #print(f"classes: {classes}")
            if "uselected" in classes:
                classes.remove("uselected")
            classes.add("selected")
            self.selected_node1.classes = " ".join(classes)
        
        #with self.out: print(f'here2')

        if self.selected_node2: 

            classes = set(self.selected_node2.classes.split(" "))
            #print(f"classes: {classes}")
            if "unselected" in classes:
                classes.remove("unselected")
            classes.add("selected")
            self.selected_node2.classes = " ".join(classes)

        #with self.out: print(f'here3')

        #with self.out: print(f"selected_node1: {self.selected_node1}")
        #with self.out: print(f"selected_node2: {self.selected_node2}")
        
        ##curr_node.classes += ' selected'
        #classes = set(curr_node.classes.split(" "))
        #if "unselected" in classes:
        #    classes.remove("unselected")
        #classes.add("selected")
        #curr_node.classes = " ".join(classes)
        
        self.redraw_node_info()
            
            
    def on_mouseover(self, node):
        pass
        #with self.out:
        #    print('mouseovers: {}'.format(str(node)))
            
    def path_btn_callback(self, btn):
        #with self.out: print(f'path_btn_callback')

        #if self.selected_node1 == None or self.selected_node2 == None:
        #    with self.out: print(f'run_btn_callback: needs to select two nodes')
        
        
        #with self.out: 
        #    print(f"run_btn_callback: testing: {self.selected_node1.data['name']} -> {self.selected_node2.data['name']}")
            
            
        with self.out: self.find_path(source_node=self.get_node(self.selected_node1.data['name']), 
                        target_node=self.get_node(self.selected_node2.data['name']), verbose=False)
        
        self.redraw_node_info()
        
    def clear_btn_callback(self, btn):
        #with self.out: print(f'clear_btn_callback')

        for node in self.cytoscapeobj.graph.nodes:
            classes = set(node.classes.split(" "))
            #print(f"classes: {classes}")
            if "selected" in classes:
                classes.remove("selected")
            classes.add("unselected")
            node.classes = " ".join(classes)
     
        self.selected_node1 = None
        self.selected_node2 = None
        
        self.redraw_node_info()
        
    def run_btn_callback(self, btn):
        
        #if self.selected_node1 == None or self.selected_node2 == None:
        #    with self.out: print(f'run_btn_callback: needs to select two nodes')
        
        
        #with self.out: 
        #    print(f"run_btn_callback: testing: {self.selected_node1.data['name']} -> {self.selected_node2.data['name']}")
            
        t=f"{self.iperf3_params_info['P'].value}"
        i=f"{self.iperf3_params_info['i'].value}"      
        O=f"{self.iperf3_params_info['O'].value}"                                            
        w=f"{self.iperf3_params_info['w'].value}m"
        P=f"{self.iperf3_params_info['P'].value}"                                               
            
        
        with self.out: self.iperf3_run(source_node=self.get_node(self.selected_node1.data['name']), 
                        target_node=self.get_node(self.selected_node2.data['name']), 
                        w=w, P=P, t=t, i=i, O=O, verbose=False)
        
        from IPython.display import clear_output
        from performance_testing.iperf3 import iperf3_process_output

        with self.out: 
            clear_output(wait=True)
            self.iperf3_process_output(verbose=False)
            #iperf3_process_output(verbose=True)
            
            
        


    def display(self):
        #update the fabric management ips
        self.update_nodes()
            
        
            
        self.selected_node1 = None
        self.selected_node2 = None
        self.cytoscape_node_map = {}
        
        self.out = Output()
    
        self.cytoscapeobj = cy.CytoscapeWidget(layout=Layout(width='70%'))
        self.data = { 'nodes': [], 'edges': [] }
        
        self.display_set_style()
        
        #node1 info (right_top), node2 info (right_middle)
        self.node1_info = { 
                             'name': widgets.Label(value=""),
                             'type': widgets.Label(value=""),
                             'facility': widgets.Label(value=""),
                             'dataplane_ip': widgets.Label(value=""),
                             'site': widgets.Label(value=""),
                             'management_ip': widgets.Label(value=""),
                           }
        self.node2_info = { 
                             'name': widgets.Label(value=""),
                             'type': widgets.Label(value=""),
                             'facility': widgets.Label(value=""),
                             'dataplane_ip': widgets.Label(value=""),
                             'site': widgets.Label(value=""),
                             'management_ip': widgets.Label(value=""),
                           }        
        
        
         
        
        
        self.node1_label = widgets.Label(value="select node1")
        self.node2_label = widgets.Label(value="select node2")
        
        self.node1_box = widgets.VBox([ HTML('<center><b>Source Node</b></center>'),
                                        widgets.HBox([widgets.Label(value="Name:"), self.node1_info['name']] ),
                                        widgets.HBox([widgets.Label(value="Facility:"), self.node1_info['facility']] ),
                                        widgets.HBox([widgets.Label(value="Site:"), self.node1_info['site']] ),
                                        widgets.HBox([widgets.Label(value="Dataplane IP:"), self.node1_info['dataplane_ip']] ),
                                        widgets.HBox([widgets.Label(value="Management IP:"), self.node1_info['management_ip']] ),
                                        widgets.HBox([widgets.Label(value="type:"), self.node1_info['type']] ),
                                      ]) 
        self.node2_box = widgets.VBox([ HTML('<center><b>Target Node</b></center>'),
                                        widgets.HBox([widgets.Label(value="Name:"), self.node2_info['name']] ),
                                        widgets.HBox([widgets.Label(value="Facility:"), self.node2_info['facility']] ),
                                        widgets.HBox([widgets.Label(value="Site:"), self.node2_info['site']] ),
                                        widgets.HBox([widgets.Label(value="Dataplane IP:"), self.node2_info['dataplane_ip']] ),
                                        widgets.HBox([widgets.Label(value="Management IP:"), self.node2_info['management_ip']] ),
                                        widgets.HBox([widgets.Label(value="Type:"), self.node2_info['type']] ),
                                      ]) 
 
        self.iperf3_params_info = { 
                             'P': widgets.IntText(value=1,description='P:', disabled=False),
                             'i': widgets.IntText(value=1,description='i:', disabled=False),
                             't': widgets.IntText(value=20,description='t:', disabled=False),
                             'O': widgets.IntText(value=10,description='O:', disabled=False),
                             'w': widgets.IntText(value=16,description='w(m):', disabled=False),
                           }        
        

        self.iperf3_params_box = widgets.VBox([ HTML('<center><b>iPerf3 Parameters</b></center>'),
                                        self.iperf3_params_info['t'],
                                        self.iperf3_params_info['i'],
                                        self.iperf3_params_info['O'],
                                        self.iperf3_params_info['w'],
                                        self.iperf3_params_info['P'],
                                      ]) 
        
    
        #controls (right_bottom)
        self.path_btn = widgets.Button(description="Find Path", disabled=False)
        self.clear_btn = widgets.Button(description="Clear", disabled=False)
        self.run_btn = widgets.Button(description="Run iPerf", disabled=False)
        self.button_hbox = widgets.HBox( [self.path_btn, self.run_btn, self.clear_btn] )

        #right
        self.right_vbox = widgets.VBox( [HTML('<center><b><hr></b></center>'), 
                                         self.node1_box, 
                                         HTML('<center><b><hr></b></center>'), 
                                         self.node2_box, 
                                         HTML('<center><b><hr></b></center>'),
                                         self.iperf3_params_box,
                                         HTML('<center><b><hr></b></center>'),
                                         self.button_hbox  ,
                                         HTML('<center><b><hr></b></center>'),
                                         self.out] )
        
        
        #top
        self.top_hbox = widgets.HBox( [self.cytoscapeobj, self.right_vbox], width='100%', min_height='300px', overflow_y='hidden')       
        

                                            

        #main vbox
        self.main_vbox = widgets.VBox( [ self.top_hbox ] )
        
        
        self.setup_interaction()
        self.build_data()
    
        
        display(self.main_vbox)
        #display(self.out)
        

    
    def create_table_local(self, table, headers=None, title='', properties={}, hide_header=False, title_font_size='1.25em', index=None):

        if headers is not None:
            df = pd.DataFrame(table, columns=headers)
        else:
            df = pd.DataFrame(table)

        if index is not None:
            df.set_index(index, inplace=True, drop=True)
            df.columns.name = df.index.name
            df.index.name = None

        if hide_header:
            style = df.style.set_caption(title).set_properties(**properties).hide(axis='index').hide(axis='columns').set_table_styles([{
                'selector': 'caption',
                'props': f'caption-side: top; font-size:{title_font_size};'
            }], overwrite=False)
        else:
            style = df.style.set_caption(title).set_properties(**properties).set_table_styles([{
                    'selector': 'caption',
                    'props': f'caption-side: top; font-size:{title_font_size};'
                }], overwrite=False)

        slice_string = style
        return slice_string



    
    def execute(self, command, 
                      retry=3, 
                      retry_interval=10, 
                      username=None, 
                      private_key_file=None, 
                      private_key_passphrase=None,
                      quiet=False,
                      read_timeout=10, 
                      timeout=None,
                      output_file=None):

        import logging

        logging.debug(f"execute node: {self.get_name()}, management_ip: {self.get_management_ip()}, command: {command}")

        if output_file:
            file = open(output_file, "a")
                    
        #if not quiet:
        chunking = True

        if self.get_fablib_manager().get_log_level() == logging.DEBUG:
            start = time.time()

        #Get and test src and management_ips
        management_ip = str(self.get_fim_node().get_property(pname='management_ip'))
        if self.validIPAddress(management_ip) == 'IPv4':
            #src_addr = (self.get_fablib_manager().get_bastion_private_ipv4_addr(), 22)
            src_addr = ('0.0.0.0',22)

        elif self.validIPAddress(management_ip) == 'IPv6':
            #src_addr = (self.get_fablib_manager().get_bastion_private_ipv6_addr(), 22)
            src_addr = ('0:0:0:0:0:0:0:0',22)
        else:
            raise Exception(f"node.execute: Management IP Invalid: {management_ip}")
        dest_addr = (management_ip, 22)


        bastion_username=self.get_fablib_manager().get_bastion_username()
        bastion_key_file=self.get_fablib_manager().get_bastion_key_filename()

        if username != None:
            node_username = username
        else:
            node_username=self.username

        if private_key_file != None:
            node_key_file = private_key_file
        else:
            node_key_file=self.get_private_key_file()

        if private_key_passphrase != None:
            node_key_passphrase = private_key_passphrase
        else:
            node_key_passphrase=self.get_private_key_file()

        for attempt in range(int(retry)):
            try:
                key = self.get_paramiko_key(private_key_file=node_key_file, get_private_key_passphrase=node_key_passphrase)
                bastion=paramiko.SSHClient()
                bastion.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                bastion.connect(self.get_fablib_manager().get_bastion_public_addr(), username=bastion_username, key_filename=bastion_key_file)

                bastion_transport = bastion.get_transport()
                bastion_channel = bastion_transport.open_channel("direct-tcpip", dest_addr, src_addr)

                client = paramiko.SSHClient()
                #client.load_system_host_keys()
                #client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(management_ip,username=node_username,pkey = key, sock=bastion_channel)

                #stdin, stdout, stderr = client.exec_command('echo \"' + command + '\" > /tmp/fabric_execute_script.sh; chmod +x /tmp/fabric_execute_script.sh; /tmp/fabric_execute_script.sh')

                if timeout is not None:
                    command = f'sudo timeout --foreground -k 10 {timeout} ' + command + '\n'

                stdin, stdout, stderr = client.exec_command(command)
                channel = stdout.channel

                # Only writing one command, so we can shut down stdin and
                # writing abilities
                stdin.close()
                channel.shutdown_write()

                # Read stdout and stderr:
                if not chunking:
                    # The old way
                    rtn_stdout = str(stdout.read(),'utf-8').replace('\\n','\n')
                    rtn_stderr = str(stderr.read(),'utf-8').replace('\\n','\n')
                    if quiet == False:
                        print(rtn_stdout, rtn_stderr)

                else:
                    # Credit to Stack Overflow user tintin's post here: https://stackoverflow.com/a/32758464
                    stdout_chunks = []
                    stdout_chunks.append(stdout.channel.recv(len(stdout.channel.in_buffer)))
                    stderr_chunks = []

                    while not channel.closed or channel.recv_ready() or channel.recv_stderr_ready(): 
                        got_chunk = False
                        readq, _, _ = select.select([stdout.channel], [], [], read_timeout)
                        for c in readq:
                            if c.recv_ready():
                                stdoutbytes = stdout.channel.recv(len(c.in_buffer))
                                if quiet == False:
                                    print(str(stdoutbytes,'utf-8').replace('\\n','\n'), end='')
                                if output_file:
                                    file.write(str(stdoutbytes,'utf-8').replace('\\n','\n'))
                                    file.flush()
                                    
                                stdout_chunks.append(stdoutbytes)
                                got_chunk = True
                            if c.recv_stderr_ready(): 
                                # make sure to read stderr to prevent stall
                                stderrbytes =  stderr.channel.recv_stderr(len(c.in_stderr_buffer))
                                if quiet == False:
                                    print('\x1b[31m',str(stderrbytes,'utf-8').replace('\\n','\n'),'\x1b[0m', end='')
                                if output_file:
                                    file.write(str(stderrbytes,'utf-8').replace('\\n','\n'))
                                    file.flush()
                                stderr_chunks.append(stderrbytes)
                                got_chunk = True

                        if not got_chunk \
                            and stdout.channel.exit_status_ready() \
                            and not stderr.channel.recv_stderr_ready() \
                            and not stdout.channel.recv_ready(): 
                            stdout.channel.shutdown_read()  
                            stdout.channel.close()
                            break

                    stdout.close()
                    stderr.close()

                    # chunks are groups of bytes, combine and convert to str
                    rtn_stdout = b''.join(stdout_chunks).decode("utf-8") 
                    rtn_stderr = b''.join(stderr_chunks).decode("utf-8") 

                client.close()
                bastion_channel.close()

                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    end = time.time()
                    logging.debug(f"Running node.execute(): command: {command}, elapsed time: {end - start} seconds")

                logging.debug(f"rtn_stdout: {rtn_stdout}")
                logging.debug(f"rtn_stderr: {rtn_stderr}")

                if output_file:
                    file.close()
                
                return rtn_stdout, rtn_stderr
                #success, skip other tries
                break
            except Exception as e:
                logging.warning(f"{e}")
                try:
                    client.close()
                except:
                    logging.debug("Exception in client.close")
                    pass
                try:
                    bastion_channel.close()
                except:
                    logging.debug("Exception in bastion_channel.close()")
                    pass

                try:
                    if output_file:
                        file.close()
                except:
                    logging.debug("Exception in output_file close()")
                    pass

                if attempt+1 == retry:
                    raise e

                #Fail, try again
                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    logging.debug(f"SSH execute fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                    logging.debug(e, exc_info=True)

                time.sleep(retry_interval)
                pass

        raise Exception("ssh failed: Should not get here")


