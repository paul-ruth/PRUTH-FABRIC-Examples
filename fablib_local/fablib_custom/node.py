#!/bin/python3

import os

import json
import time
import paramiko


import pandas as pd
from tabulate import tabulate

import logging

from fabrictestbed.util.constants import Constants
from concurrent.futures import ThreadPoolExecutor

from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)


import select

#from fablib_local_imports.fablib_plugin_methods.node import *
#from fablib_local_imports.fablib_plugin_methods.interface import *
#from fablib_local_imports.fablib_plugin_methods.slice import *

class Node_Custom():

    def place_holder():
        pass

    def get_userdata(self):
        return list(filter(lambda x: x['name'] ==  self.get_name(), self.get_slice().userdata['nodes']))[0]
        
    def init_userdata(self):
        node_userdata = self.get_userdata()
        
        node_userdata['static_routes'] = []
    
    def add_static_route(self, subnet, gateway):
        
        try:
            slice_userdata = self.get_slice().get_userdata()
            node_userdata = self.get_userdata()

            print(f"slice_userdata: {json.dumps(slice_userdata, indent=4)}")
            print(f"node_userdata: {json.dumps(node_userdata, indent=4)  }")

            network_userdata = list(filter(lambda x: x['gateway'] == gateway, slice_userdata['networks']))[0]
            print(f"network_userdata: {json.dumps(network_userdata, indent=4)   }")

            interface_userdata = list(filter(lambda x: x['network'] == network_userdata['name'], slice_userdata['interfaces']))[0]
            print(f"interface_userdata: {json.dumps(interface_userdata, indent=4)   }")

            dev = interface_userdata['dev']
            print(f"dev: {dev}")

            if 'static_routes' not in node_userdata:
                node_userdata['static_routes'] = []

            node_userdata['static_routes'].append({ 'subnet': subnet, 'gateway': gateway })

            #gateway = network_userdata['gateway']
            self.execute( f'sudo nmcli connection mod {dev} +ipv4.routes "{subnet} {gateway}" ;'
                          f'sudo nmcli con down {dev} ;'
                          f'sudo nmcli con up {dev} ;', quiet=True)
        except Exception as e:
            logging.error(f"Faled to add static route {node.get_name()}, {subnet} {gatewau}")
        
   
        
# Add methods to FABlib Classes
from fabrictestbed_extensions.fablib.node import Node

#fablib.Node
setattr(Node, 'add_static_route', Node_Custom.add_static_route)
setattr(Node, 'get_userdata', Node_Custom.get_userdata)
setattr(Node, 'init_userdata', Node_Custom.init_userdata)

#setattr(Node, 'get_paramiko_key', Node_Custom.get_paramiko_key)
#setattr(Node, 'execute', Node_Custom.execute)


