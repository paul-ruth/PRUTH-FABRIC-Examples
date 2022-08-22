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


class FablibManager_Custom():
    
    # ##### From Brandons plugins file ##########

    def print_table(self, table, headers=None, title='', properties={}, hide_header=False, title_font_size='1.25em', index=None):
        if(self.output_type.lower() == 'text'):
            print(f"\n{self.create_table(table, headers=headers, title=title, properties=properties, hide_header=hide_header, title_font_size=title_font_size,index=index)}")

        elif(self.output_type.lower() == 'html'):
            display(self.create_table(table, headers=headers, title=title, properties=properties, hide_header=hide_header, title_font_size=title_font_size,index=index))


    def create_table(self, table, headers=None, title='', properties={}, hide_header=False, title_font_size='1.25em', index=None):
        if(self.output_type.lower() == 'text'):
            if headers is not None:
                slice_string = tabulate(table, headers=headers)
            else:
                slice_string = tabulate(table)
            return slice_string

        elif(self.output_type.lower() == 'html'):
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

    def show_config(self):
        table = []
        for var, val in self.get_config().items():
            table.append([str(var), str(val)])

        self.print_table(table, title='User Configuration for FABlib Manager', properties={'text-align': 'left', 'border': '1px black solid !important'}, hide_header=True)


    def __init__(self,
                 fabric_rc=None,
                 credmgr_host=None,
                 orchestrator_host=None,
                 fabric_token=None,
                 project_id=None,
                 bastion_username=None,
                 bastion_key_filename=None,
                 log_level=None,
                 log_file=None,
                 data_dir=None,
                 output_type='text'):
        """
        Constructor. Builds FablibManager.  Tries to get configuration from:

         - constructor parameters (high priority)
         - fabric_rc file (middle priority)
         - environment variables (low priority)
         - defaults (if needed and possible)

        """
        # super().__init__() #FIXME: Remove from original code?

        self.output_type = output_type

        #initialized thread pool for ssh connections
        self.ssh_thread_pool_executor = ThreadPoolExecutor(10)

        # init attributes
        self.bastion_passphrase = None
        self.log_file = self.default_log_file
        self.log_level = self.default_log_level
        self.set_log_level(self.log_level)

        #self.set_log_file(log_file)
        self.data_dir = data_dir

        # Setup slice key dict
        # self.slice_keys = {}
        self.default_slice_key = {}

        # Set config values from env vars
        if Constants.FABRIC_CREDMGR_HOST in os.environ:
            self.credmgr_host = os.environ[Constants.FABRIC_CREDMGR_HOST]

        if Constants.FABRIC_ORCHESTRATOR_HOST in os.environ:
            self.orchestrator_host = os.environ[Constants.FABRIC_ORCHESTRATOR_HOST]

        if Constants.FABRIC_TOKEN_LOCATION in os.environ:
            self.fabric_token = os.environ[Constants.FABRIC_TOKEN_LOCATION]

        if Constants.FABRIC_PROJECT_ID in os.environ:
            self.project_id = os.environ[Constants.FABRIC_PROJECT_ID]

        # Basstion host setup
        if self.FABRIC_BASTION_USERNAME in os.environ:
            self.bastion_username = os.environ[self.FABRIC_BASTION_USERNAME]
        if self.FABRIC_BASTION_KEY_LOCATION in os.environ:
            self.bastion_key_filename = os.environ[self.FABRIC_BASTION_KEY_LOCATION]
        if self.FABRIC_BASTION_HOST in os.environ:
            self.bastion_public_addr = os.environ[self.FABRIC_BASTION_HOST]
        # if self.FABRIC_BASTION_HOST_PRIVATE_IPV4 in os.environ:
        #    self.bastion_private_ipv4_addr = os.environ[self.FABRIC_BASTION_HOST_PRIVATE_IPV4]
        # if self.FABRIC_BASTION_HOST_PRIVATE_IPV6 in os.environ:
        #    self.bastion_private_ipv6_addr = os.environ[self.FABRIC_BASTION_HOST_PRIVATE_IPV6]

        # Slice Keys
        if self.FABRIC_SLICE_PUBLIC_KEY_FILE in os.environ:
            self.default_slice_key['slice_public_key_file'] = os.environ[self.FABRIC_SLICE_PUBLIC_KEY_FILE]
            with open(os.environ[self.FABRIC_SLICE_PUBLIC_KEY_FILE], "r") as fd:
                self.default_slice_key['slice_public_key'] = fd.read().strip()
        if self.FABRIC_SLICE_PRIVATE_KEY_FILE in os.environ:
            # self.slice_private_key_file=os.environ['FABRIC_SLICE_PRIVATE_KEY_FILE']
            self.default_slice_key['slice_private_key_file'] = os.environ[self.FABRIC_SLICE_PRIVATE_KEY_FILE]
        if "FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE" in os.environ:
            # self.slice_private_key_passphrase = os.environ['FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE']
            self.default_slice_key['slice_private_key_passphrase'] = os.environ[
                self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE]

        # Set config values from fabric_rc file
        if fabric_rc == None:
            fabric_rc = self.default_fabric_rc

        fabric_rc_dict = self.read_fabric_rc(fabric_rc)

        if Constants.FABRIC_CREDMGR_HOST in fabric_rc_dict:
            self.credmgr_host = fabric_rc_dict[Constants.FABRIC_CREDMGR_HOST]

        if Constants.FABRIC_ORCHESTRATOR_HOST in fabric_rc_dict:
            self.orchestrator_host = fabric_rc_dict[Constants.FABRIC_ORCHESTRATOR_HOST]

        if 'FABRIC_TOKEN_LOCATION' in fabric_rc_dict:
            self.fabric_token = fabric_rc_dict['FABRIC_TOKEN_LOCATION']
            os.environ[Constants.FABRIC_TOKEN_LOCATION] = self.fabric_token

        if 'FABRIC_PROJECT_ID' in fabric_rc_dict:
            self.project_id = fabric_rc_dict['FABRIC_PROJECT_ID']
            os.environ['FABRIC_PROJECT_ID'] = self.project_id

        # Basstion host setup
        if self.FABRIC_BASTION_HOST in fabric_rc_dict:
            self.bastion_public_addr = fabric_rc_dict[self.FABRIC_BASTION_HOST]
        if self.FABRIC_BASTION_USERNAME in fabric_rc_dict:
            self.bastion_username = fabric_rc_dict[self.FABRIC_BASTION_USERNAME]
        if self.FABRIC_BASTION_KEY_LOCATION in fabric_rc_dict:
            self.bastion_key_filename = fabric_rc_dict[self.FABRIC_BASTION_KEY_LOCATION]
        if self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE in fabric_rc_dict:
            self.bastion_key_filename = fabric_rc_dict[self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE]

        # Slice keys
        if self.FABRIC_SLICE_PRIVATE_KEY_FILE in fabric_rc_dict:
            self.default_slice_key['slice_private_key_file'] = fabric_rc_dict[self.FABRIC_SLICE_PRIVATE_KEY_FILE]
        if self.FABRIC_SLICE_PUBLIC_KEY_FILE in fabric_rc_dict:
            self.default_slice_key['slice_public_key_file'] = fabric_rc_dict[self.FABRIC_SLICE_PUBLIC_KEY_FILE]
            with open(fabric_rc_dict[self.FABRIC_SLICE_PUBLIC_KEY_FILE], "r") as fd:
                self.default_slice_key['slice_public_key'] = fd.read().strip()
        if self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE in fabric_rc_dict:
            self.default_slice_key['slice_private_key_passphrase'] = fabric_rc_dict[
                self.FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE]

        if self.FABRIC_LOG_FILE in fabric_rc_dict:
            self.set_log_file(fabric_rc_dict[self.FABRIC_LOG_FILE])
        if self.FABRIC_LOG_LEVEL in fabric_rc_dict:
            self.set_log_level(fabric_rc_dict[self.FABRIC_LOG_LEVEL])

        # Set config values from constructor arguments
        if credmgr_host != None:
            self.credmgr_host = credmgr_host
        if orchestrator_host != None:
            self.orchestrator_host = orchestrator_host
        if fabric_token != None:
            self.fabric_token = fabric_token
        if project_id != None:
            self.project_id = project_id
        if bastion_username != None:
            self.bastion_username = bastion_username
        if bastion_key_filename != None:
            self.bastion_key_filename = bastion_key_filename
        if log_level != None:
            self.set_log_level(log_level)
        if log_file != None:
            self.set_log_file(log_file)
        if data_dir != None:
            self.data_dir = data_dir

        # self.bastion_private_ipv4_addr = '0.0.0.0'
        # self.bastion_private_ipv6_addr = '0:0:0:0:0:0'

        # Create slice manager
        self.slice_manager = None
        self.resources = None
        self.build_slice_manager()

    
# #################################################



# Add methods to FABlib Classes
from fabrictestbed_extensions.fablib.fablib import FablibManager

#fablib.Slice


setattr(FablibManager, 'print_table', FablibManager_Custom.print_table )
setattr(FablibManager, 'create_table', FablibManager_Custom.create_table )


setattr(FablibManager, 'show_config', FablibManager_Custom.show_config)
setattr(FablibManager, '__init__', FablibManager_Custom.__init__)



            
