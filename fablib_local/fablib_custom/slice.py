#!/bin/python3

import os

import json
import time
import paramiko

import logging

import pandas as pd
from tabulate import tabulate

from fabrictestbed.util.constants import Constants
from concurrent.futures import ThreadPoolExecutor

from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)

class Slice_Custom():

    def list_nodes_tabulate(self, quiet=False):
        """
        Creates a tabulated string describing all nodes in the slice.

        Intended for printing a list of all slices.

        :return: Tabulated srting of all slices information
        :rtype: String
        """
        table = []
        for node in self.get_nodes():

            table.append( [     node.get_reservation_id(),
                                node.get_name(),
                                node.get_site(),
                                node.get_host(),
                                node.get_cores(),
                                node.get_ram(),
                                node.get_disk(),
                                node.get_image(),
                                node.get_management_ip(),
                                node.get_reservation_state(),
                                node.get_error_message(),
                                ] )

        output = tabulate(table, headers=["ID", "Name",  "Site",  "Host", "Cores", "RAM", "Disk", "Image", "Management IP", "State", "Error"])

        if not quiet:
            print(f'{output}') 

        return output

    def list_nodes_pandas(self, quiet=False):
        reservation_ids = []
        names = []
        sites = []
        hosts = []
        cores = []
        rams = []
        disks = []
        images = []
        management_ips = []
        reservation_states = []
        error_messages = []

        # build lists
        for node in self.get_nodes():
            reservation_ids.append(node.get_reservation_id())
            names.append(node.get_name())
            sites.append(node.get_site())
            hosts.append(node.get_host())
            cores.append(node.get_cores())
            rams.append(node.get_ram())
            disks.append(node.get_disk())
            images.append(node.get_image())
            management_ips.append(node.get_management_ip())
            reservation_states.append(node.get_reservation_state())
            error_messages.append(node.get_error_message())

        # build dataframe

        columns = ["ID", "Name",  "Site",  "Host", "Cores", "RAM", "Disk", "Image", "Management IP", "State", "Error"]
        df = pd.DataFrame(list(zip(reservation_ids, names, sites, hosts, cores, rams, disks, images, management_ips, reservation_states,error_messages)), columns = columns)
        #pd.set_option('colheader_justify', 'left')
        #df = df.style.set_properties(**{'text-align': 'left'})

        dfStyler = df.style.set_properties(**{'text-align': 'left'})
        dfStyler.set_table_styles([dict(selector='th', props=[('text-align', 'left')])])


        if not quiet:
            display(df)

        return df


    def list_resouces_pandas(self, quiet=False):
        import pandas as pd
        #  initialize lists
        cpus = []
        cores = []
        ram = []
        disk = []
        basicNic = []
        connectX6Nic = []
        connectX5Nic = []
        p4510 = []
        tesla = []
        rtx6000 = []
        available_resources = self.get_available_resources()
        siteNames = available_resources.get_site_list()

        # build lists
        for site in siteNames:
            cpus.append(available_resources.get_cpu_capacity(site))
            cores.append(f'{available_resources.get_core_available(site)}/{available_resources.get_core_capacity(site)}')
            ram.append(f'{available_resources.get_ram_available(site)}/{available_resources.get_ram_capacity(site)}')
            disk.append(f'{available_resources.get_disk_available(site)}/{available_resources.get_disk_capacity(site)}')
            basicNic.append(f'{available_resources.get_component_available(site,"SharedNIC-ConnectX-6")}/{available_resources.get_component_capacity(site, "SharedNIC-ConnectX-6")}')
            connectX6Nic.append(f'{available_resources.get_component_available(site, "SmartNIC-ConnectX-6")}/{available_resources.get_component_capacity(site, "SmartNIC-ConnectX-6")}')
            connectX5Nic.append(f'{available_resources.get_component_available(site, "SmartNIC-ConnectX-5")}/{available_resources.get_component_capacity(site, "SmartNIC-ConnectX-5")}')
            p4510.append(f'{available_resources.get_component_available(site, "NVME-P4510")}/{available_resources.get_component_capacity(site, "NVME-P4510")}')
            tesla.append(f'{available_resources.get_component_available(site, "GPU-Tesla T4")}/{available_resources.get_component_capacity(site, "GPU-Tesla T4")}')
            rtx6000.append(f'{available_resources.get_component_available(site, "GPU-RTX6000")}/{available_resources.get_component_capacity(site, "GPU-RTX6000")}')

        # build dataframe

        columns = ['Site Name', 'CPUs', 'Cores', 'RAM (G)', 'Disk (G)', 'Basic (100 Gbps NIC)', 'ConnectX-6 (100 Gbps x2 NIC)', 'ConnectX-5 (25 Gbps x2 NIC)', 'P4510 (NVMe 1TB)', 'Tesla T4 (GPU)', 'RTX6000 (GPU)']
        df = pd.DataFrame(list(zip(siteNames, cpus, cores, ram, disk, basicNic, connectX6Nic, connectX5Nic,p4510, tesla, rtx6000)), columns = columns)
        pd.set_option('colheader_justify', 'center')
        df = df.style.set_properties(**{'text-align': 'center'})

        df2 = df
        if not quiet:
            display(df)
            display(df2)


        return df


    def list_nodes(self, style='tabulate', quiet=False):

        if style == 'tabulate':
            return self.list_nodes_tabulate(quiet=quiet)
        elif style == 'pandas':
            return self.list_nodes_pandas(quiet=quiet)






    # fablib.Slice.get_slice_id()
    def get_slice_id(self):
        return self.slice_id
    

    def submit(self, wait=True, wait_timeout=600, wait_interval=10, progress=True, wait_jupyter="text"):
        """
        Submits a slice request to FABRIC.

        Can be blocking or non-blocking.

        Blocking calls can, optionally,configure timeouts and intervals.

        Blocking calls can, optionally, print progress info.


        :param wait: indicator for whether to wait for the slice's resources to be active
        :type wait: bool
        :param wait_timeout: how many seconds to wait on the slice resources
        :type wait_timeout: int
        :param wait_interval: how often to check on the slice resources
        :type wait_interval: int
        :param progress: indicator for whether to show progress while waiting
        :type progress: bool
        :param wait_jupyter: Special wait for jupyter notebooks.
        :type wait_jupyter: String
        :return: slice_id
        :rtype: String
        """
        from fabrictestbed_extensions.fablib.fablib import fablib
        
        if not wait:
            progress = False

        # Generate Slice Graph
        slice_graph = self.get_fim_topology().serialize()

        # Request slice from Orchestrator
        return_status, slice_reservations = self.fablib_manager.get_slice_manager().create(slice_name=self.slice_name,
                                                                slice_graph=slice_graph,
                                                                ssh_key=self.get_slice_public_key())
        if return_status != Status.OK:
            raise Exception("Failed to submit slice: {}, {}".format(return_status, slice_reservations))

        logging.debug(f'slice_reservations: {slice_reservations}')
        logging.debug(f"slice_id: {slice_reservations[0].slice_id}")
        self.slice_id = slice_reservations[0].slice_id

        time.sleep(1)
        #self.update_slice()
        self.update()

        if progress and wait_jupyter == 'text' and self.fablib_manager.isJupyterNotebook():
            self.wait_jupyter(timeout=wait_timeout, interval=wait_interval)
            return self.slice_id

        if wait:
            self.wait_ssh(timeout=wait_timeout,interval=wait_interval,progress=progress)

            if progress:
                print("Running post boot config ... ",end="")

            self.update()
            #self.test_ssh()
            self.post_boot_config()

        if progress:
            print("Done! from Local Submit")


        return self.slice_id




    ######## FROM Brandon's plugins file ##########

    def wait_jupyter(self, timeout=600, interval=10):
        from IPython.display import clear_output
        import time
        import random
        global fablib

        start = time.time()

        count = 0
        while not self.isStable():
            if time.time() > start + timeout:
                raise Exception(f"Timeout {timeout} sec exceeded in Jupyter wait")

            time.sleep(interval)
            self.update()
            # node_list = self.list_nodes()

            #pre-get the strings for quicker screen update
            # slice_string=str(self)
            
            print(f"sm_slice: {self.sm_slice}")

            table = [["Slice Name", self.sm_slice.name],
                 ["Slice ID", self.sm_slice.slice_id],
                 ["Slice State", self.sm_slice.state],
                 ["Lease End (UTC)", self.sm_slice.lease_end_time]
                ]

            time_string = f"{time.time() - start:.0f} sec"

            # Clear screen
            clear_output(wait=True)

            #Print statuses
            self.get_fablib_manager().print_table(table, title='Slice Reservation Status', properties={'text-align': 'left', 'border': '1px black solid !important'}, hide_header=True, title_font_size='1.25em')

            print(f"\nRetry: {count}, Time: {time_string}")

            self.list_nodes()

            count += 1

        print(f"\nTime to stable {time.time() - start:.0f} seconds")

        #print("Running wait_ssh ... ", end="")
        #self.wait_ssh()
        #print(f"Time to ssh {time.time() - start:.0f} seconds")

        print("Running post_boot_config ... ", end="")
        self.post_boot_config()
        print(f"Time to post boot config {time.time() - start:.0f} seconds")

        if len(self.get_interfaces()) > 0:
            print(f"\n{self.list_interfaces()}")
            print(f"\nTime to print interfaces {time.time() - start:.0f} seconds")


    def list_nodes(self, verbose=False):
        if not verbose:
            table = []
            for node in self.get_nodes():

                table.append( [     node.get_reservation_id(),
                                    node.get_name(),
                                    node.get_site(),
                                    node.get_host(),
                                    node.get_cores(),
                                    node.get_ram(),
                                    node.get_disk(),
                                    node.get_image(),
                                    node.get_management_ip(),
                                    node.get_reservation_state(),
                                    node.get_error_message(),
                                    ] )

            headers=["ID", "Name",  "Site",  "Host", "Cores", "RAM", "Disk", "Image",
                                            "Management IP", "State", "Error"]
            printable_table = self.get_fablib_manager().create_table(table, title=f'List of Nodes in {self.get_name()}', properties={'text-align': 'left'}, headers=headers, index='Name')


            if(self.get_fablib_manager().output_type.lower() == 'text'):
                print(printable_table)
                return

            elif(self.get_fablib_manager().output_type.lower() == 'html'):
                def highlight(x):
                    if x.State == 'Ticketed':
                        return ['background-color: yellow']*(len(headers)-1)
                    elif x.State == 'None':
                        return ['opacity: 50%']*(len(headers)-1)
                    else:
                        return ['background-color: ']*(len(headers)-1)

                def green_active(val):
                    if val == 'Active':
                        color = 'green'
                    else:
                        color = 'black'
                    return 'color: %s' % color

                printable_table = printable_table.apply(highlight, axis=1).applymap(green_active, subset=pd.IndexSlice[:, ['State']]).set_properties(**{'text-align': 'left'})

                display(printable_table)
                return

        else:
            col = [ "Name",
                    "Site", 
                    "ID", 
                    "Cores", 
                    "RAM", 
                    "Disk", 
                    "Image", 
                    "SSH Command",
                    "Image Type",
                    "Host", 
                    "Management IP",
                    "Reservation State",
                    "Error Message"
                    ]

            df = pd.DataFrame()

            for node in self.get_nodes():
                table = [   [node.get_name()],
                            [node.get_site()],
                            [node.get_reservation_id()],
                            [node.get_cores()],
                            [node.get_ram()],
                            [node.get_disk()],
                            [node.get_image()],
                            [node.get_ssh_command()],
                            [node.get_image_type()],
                            [node.get_host()],
                            [node.get_management_ip()],
                            [node.get_reservation_state()],
                            [node.get_error_message()]
                            ]

                table = [*zip(*table)]
                df2 = pd.DataFrame(table, columns=col)

                df = pd.concat([df, df2], ignore_index = True)

            df.set_index('Name', inplace=True, drop=True)
            df.columns.name = df.index.name
            df.index.name = None

            if(self.get_fablib_manager().output_type.lower() == 'text'):
                print(df.to_string())

            elif(self.get_fablib_manager().output_type.lower() == 'html'):
                tt = pd.DataFrame([['','','','','','','The command to use to connect to the node via SSH. Copy, paste, and run this command in a terminal.','','','The IP address used to connect to the node from outside the FABRIC network. This is not the IP address used to connect between nodes in the FABRIC network.','','']],
                    index=df.index, columns=df.columns)

                style = df.style.set_caption(f"{self.get_name()} Node Information").set_properties(**{'text-align': 'left', 'white-space': 'nowrap', 'border': '1px black solid !important'}).set_sticky(axis='index').set_table_styles([{
                        'selector': 'caption',
                        'props': 'caption-side: top; font-size:1.25em;'
                    }], overwrite=False).set_tooltips(tt, props='visibility: hidden; position: absolute; z-index: 1; border: 1px solid #000066;'
                            'background-color: white; color: #000066; font-size: 1.2em;'
                            'transform: translate(-200%, -50px); padding: 0.6em; border-radius: 0.5em; white-space: nowrap;')

                display(style)
            return


    def show(self):
        table = [["Slice Name", self.sm_slice.slice_name],
                 ["Slice ID", self.sm_slice.slice_id],
                 ["Slice State", self.sm_slice.slice_state],
                 ["Lease End (UTC)", self.sm_slice.lease_end]
                ]

        self.get_fablib_manager().print_table(table, title='Slice Information', properties={'text-align': 'left', 'border': '1px black solid !important'}, hide_header=True)


    def list_interfaces(self):
        from concurrent.futures import ThreadPoolExecutor

        executor = ThreadPoolExecutor(10)

        net_name_threads = {}
        node_name_threads = {}
        physical_os_interface_name_threads = {}
        os_interface_threads = {}
        for iface in self.get_interfaces():
            if iface.get_network():
                logging.info(f"Starting get network name thread for iface {iface.get_name()} ")
                net_name_threads[iface.get_name()] = executor.submit(iface.get_network().get_name)

            if iface.get_node():
                logging.info(f"Starting get node name thread for iface {iface.get_name()} ")
                node_name_threads[iface.get_name()] = executor.submit(iface.get_node().get_name)

            logging.info(f"Starting get physical_os_interface_name_threads for iface {iface.get_name()} ")
            physical_os_interface_name_threads[iface.get_name()] = executor.submit(iface.get_physical_os_interface_name)

            logging.info(f"Starting get get_os_interface_threads for iface {iface.get_name()} ")
            os_interface_threads[iface.get_name()] = executor.submit(iface.get_os_interface)

        table = []
        for iface in self.get_interfaces():

            if iface.get_network():
                #network_name = iface.get_network().get_name()
                logging.info(f"Getting results from get network name thread for iface {iface.get_name()} ")
                network_name = net_name_threads[iface.get_name()].result()
            else:
                network_name = None

            if iface.get_node():
                #node_name = iface.get_node().get_name()
                logging.info(f"Getting results from get node name thread for iface {iface.get_name()} ")
                node_name = node_name_threads[iface.get_name()].result()

            else:
                node_name = None

            table.append( [     iface.get_name(),
                                node_name,
                                network_name,
                                iface.get_bandwidth(),
                                iface.get_vlan(),
                                iface.get_mac(),
                                physical_os_interface_name_threads[iface.get_name()].result(),
                                os_interface_threads[iface.get_name()].result(),
                                ] )

        headers=["Name", "Node", "Network", "Bandwidth", "VLAN", "MAC", "Physical OS Interface", "OS Interface"]
        self.get_fablib_manager().print_table(table, title='Slice Interfaces Information', properties={'text-align': 'left'}, headers=headers, index='Name')


    def node_show(self):
        table = [ ["ID", self.get_reservation_id()],
            ["Name", self.get_name()],
            ["Cores", self.get_cores()],
            ["RAM", self.get_ram()],
            ["Disk", self.get_disk()],
            ["Image", self.get_image()],
            ["Image Type", self.get_image_type()],
            ["Host", self.get_host()],
            ["Site", self.get_site()],
            ["Management IP", self.get_management_ip()],
            ["Reservation State", self.get_reservation_state()],
            ["Error Message", self.get_error_message()],
            ["SSH Command ", self.get_ssh_command()],
            ]

        self.get_fablib_manager().print_table(table, title='Node Information', properties={'text-align': 'left', 'border': '1px black solid !important'}, hide_header=True)


    ##################################################



# Add methods to FABlib Classes
from fabrictestbed_extensions.fablib.slice import Slice

#fablib.Slice
setattr(Slice, 'wait_jupyter', Slice_Custom.wait_jupyter)
setattr(Slice, 'show', Slice_Custom.show)
setattr(Slice, 'list_interfaces', Slice_Custom.list_interfaces)

setattr(Slice, 'get_slice_id', Slice_Custom.get_slice_id)
setattr(Slice, 'list_nodes_pandas', Slice_Custom.list_nodes_pandas)
setattr(Slice, 'list_nodes_tabulate', Slice_Custom.list_nodes_tabulate)
setattr(Slice, 'list_nodes', Slice_Custom.list_nodes)

            
