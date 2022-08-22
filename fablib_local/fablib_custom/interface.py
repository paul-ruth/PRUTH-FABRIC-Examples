#!/bin/python3

import os

import json
import time
import paramiko


import pandas as pd
from tabulate import tabulate

from fabrictestbed.util.constants import Constants
from concurrent.futures import ThreadPoolExecutor

from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)

class Interface_Custom():




    # fablib.Interface.get_ip_link()
    def get_ip_link(self):
        try:
            stdout, stderr = self.get_node().execute('ip -j link list')

            links = json.loads(stdout)

            dev = self.get_os_interface()
            if dev == None:
                return links

            for link in links:
                if link['ifname'] == dev:
                    return link
            return None    
        except Exception as e:
            print(f"Exception: {e}")

    # fablib.Interface.get_ip_addr()
    def get_ip_addr(self):
        try:
            stdout, stderr = self.get_node().execute('ip -j addr list')

            addrs = json.loads(stdout)

            dev = self.get_os_interface()
            #print(f"dev: {dev}")            

            if dev == None:
                return addrs

            for addr in addrs:
                if addr['ifname'] == dev:
                    return addr['addr_info'][0]['local']

            return None    
        except Exception as e:
            print(f"Exception: {e}")


    # fablib.Interface.get_ip_addr()
    def get_ips(self, family=None):
        return_ips = []
        try:
            dev = self.get_os_interface()

            ip_addr = self.get_ip_addr()

            #print(f"{ip_addr}")

            for addr_info in ip_addr['addr_info']:
                if family == None:
                    return_ips.append(addr_info['local'])
                else:
                    if addr_info['family'] == family:
                        return_ips.append(addr_info['local'])        
        except Exception as e:
            print(f"Exception: {e}")

        return return_ips





# Add methods to FABlib Classes
from fabrictestbed_extensions.fablib.interface import Interface


#fablib.Interface
setattr(Interface, 'get_ip_link', Interface_Custom.get_ip_link)
setattr(Interface, 'get_ip_addr', Interface_Custom.get_ip_addr)
setattr(Interface, 'get_ips', Interface_Custom.get_ips)


