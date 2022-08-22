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

class Resources_Custom():

    # ##### From Brandons plugins file ###########
    def list(self):
        table = []
        for site_name, site in self.topology.sites.items():
            #logging.debug(f"site -- {site}")
            table.append( [     site.name,
                                self.get_cpu_capacity(site_name),
                                f"{self.get_core_available(site_name)}/{self.get_core_capacity(site_name)}",
                                f"{self.get_ram_available(site_name)}/{self.get_ram_capacity(site_name)}",
                                f"{self.get_disk_available(site_name)}/{self.get_disk_capacity(site_name)}",
                                #self.get_host_capacity(site_name),
                                #self.get_location_postal(site_name),
                                #self.get_location_lat_long(site_name),
                                f"{self.get_component_available(site_name,'SharedNIC-ConnectX-6')}/{self.get_component_capacity(site_name,'SharedNIC-ConnectX-6')}",
                                f"{self.get_component_available(site_name,'SmartNIC-ConnectX-6')}/{self.get_component_capacity(site_name,'SmartNIC-ConnectX-6')}",
                                f"{self.get_component_available(site_name,'SmartNIC-ConnectX-5')}/{self.get_component_capacity(site_name,'SmartNIC-ConnectX-5')}",
                                f"{self.get_component_available(site_name,'NVME-P4510')}/{self.get_component_capacity(site_name,'NVME-P4510')}",
                                f"{self.get_component_available(site_name,'GPU-Tesla T4')}/{self.get_component_capacity(site_name,'GPU-Tesla T4')}",
                                f"{self.get_component_available(site_name,'GPU-RTX6000')}/{self.get_component_capacity(site_name,'GPU-RTX6000')}",
                                ] )

        headers=["Name",
                "CPUs",
                "Cores",
                f"RAM ({Capacities.UNITS['ram']})",
                f"Disk ({Capacities.UNITS['disk']})",
                #"Workers"
                #"Physical Address",
                #"Location Coordinates"
                "Basic (100 Gbps NIC)",
                "ConnectX-6 (100 Gbps x2 NIC)",
                "ConnectX-5 (25 Gbps x2 NIC)",
                "P4510 (NVMe 1TB)",
                "Tesla T4 (GPU)",
                "RTX6000 (GPU)",
                ]

        self.get_fablib_manager().print_table(table, title=f'Current Available Resources', properties={'text-align': 'left'}, headers=headers, index='Name')

    # #################################################



# Add methods to FABlib Classes
from fabrictestbed_extensions.fablib.resources import Resources

#fablib.Slice
setattr(Resources, 'list', Resources_Custom.list )



            
