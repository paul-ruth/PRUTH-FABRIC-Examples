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


class NetworkService_Custom():
    
    @staticmethod
    def validate_nstype(type, interfaces):
        """
        Not inteded for API use


        Verifies the network service type against the number of interfaces.

        :param type: the network service type to check
        :type type: ServiceType
        :param interfaces: the list of interfaces to check
        :type interfaces: list[Interface]
        :raises Exception: if the network service type is invalid based on the number of interfaces
        :return: true if the network service type is valid based on the number of interfaces
        :rtype: bool
        """

        # Hack for testing
        return True

        sites = set([])
        nics = set([])
        nodes = set([])
        for interface in interfaces:
            try:
                sites.add(interface.get_site())
                nics.add(interface.get_model())
                nodes.add(interface.get_node())
            except Excpetion as e:
                logging.info(f"validate_nstype: skipping interface {interface.get_name()}, likely its a facility port")
            

        # models: 'NIC_Basic', 'NIC_ConnectX_6', 'NIC_ConnectX_5'
        if type == NetworkService.network_service_map['L2Bridge']:
            if not len(sites) == 1:
                raise Exception(f"Network type {type} must include interfaces from exactly one site. {len(sites)} sites requested: {sites}")

        elif type == NetworkService.network_service_map['L2PTP']:
            if not len(sites) == 2:
                raise Exception(f"Network type {type} must include interfaces from exactly two sites. {len(sites)} sites requested: {sites}")
            if 'NIC_Basic' in nics:
                raise Exception(f"Network type {type} does not support interfaces of type 'NIC_Basic'")

        elif type == NetworkService.network_service_map['L2STS']:
            exception_list = []
            if  len(sites) != 2:
                exception_list.append(f"Network type {type} must include interfaces from exactly two sites. {len(sites)} sites requested: {sites}")
            if len(interfaces) > 2:
                hosts = set([])
                for interface in interfaces:
                    node = interface.get_node()
                    if interface.get_model() == 'NIC_Basic':
                        if node.get_host() == None:
                            exception_list.append(f"Network type {type} does not support multiple NIC_Basic interfaces on VMs residing on the same host. Please see Node.set_host(host_nane) to explicitily bind a nodes to a specific host. Node {node.get_name()} is unbound.")
                        elif node.get_host() in hosts:
                            exception_list.append(f"Network type {type} does not support multiple NIC_Basic interfaces on VMs residing on the same host. Please see Node.set_host(host_nane) to explicitily bind a nodes to a specific host. Multiple nodes bound to {node.get_host()}.")
                        else:
                            hosts.add(node.get_host())

            if len(exception_list) > 0:
                raise Exception(f"{exception_list}")
        else:
            raise Exception(f"Unknown network type {type}")

        return True
    

    # ##### From Brandons plugins file ###########
    def show(self):
        table = [ ["ID", self.get_reservation_id()],
            ["Name", self.get_name()],
            ["Layer", self.get_layer()],
            ["Type", self.get_type()],
            ["Site", self.get_site()],
            ["Gateway", self.get_gateway()],
            ["L3 Subnet", self.get_subnet()],
            ["Reservation State", self.get_reservation_state()],
            ["Error Message", self.get_error_message()],
            ]

        self.get_fablib_manager().print_table(table, title='Network Information', properties={'text-align': 'left', 'border': '1px black solid !important'}, hide_header=True)

    # #################################################



# Add methods to FABlib Classes
from fabrictestbed_extensions.fablib.network_service import NetworkService

#fablib.Slice
setattr(NetworkService, 'show', NetworkService_Custom.show )
setattr(NetworkService, 'validate_nstype', NetworkService_Custom.validate_nstype )



            
