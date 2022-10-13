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


class FacilityPort_Custom():



    # fablib.Slice.get_slice_id()
    def get_vlan(self):

        self.fim_interface.get_property(pname='label_allocations').vlan

        fim_facility_port = slice.get_fim_topology().add_facility(name=name, 
                                                                  site=site,
                                                                  capacities=Capacities(bw=bandwidth),
                                                                  labels=Labels(vlan=vlan))


        return self.slice_id




# Add methods to FABlib Classes
from fabrictestbed_extensions.fablib.faclity_port import FacilityPort


#fablib.FacilityPort
setattr(FacilityPort, 'get_vlan', FacilityPort_Custom.get_vlan)




