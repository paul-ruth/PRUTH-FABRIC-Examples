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



            
