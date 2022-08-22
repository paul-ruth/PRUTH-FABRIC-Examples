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


import select

#from fablib_local_imports.fablib_plugin_methods.node import *
#from fablib_local_imports.fablib_plugin_methods.interface import *
#from fablib_local_imports.fablib_plugin_methods.slice import *

class Node_Custom():

    # fablib.Node.get_ip_routes()
    def get_ip_routes(self):
        try:
            stdout, stderr = self.execute('ip -j route list')
            return json.loads(stdout)
        except Exception as e:
            print(f"Exception: {e}")



    # fablib.Node.get_ip_addrs()
    def get_ip_addrs(self):
        try:
            stdout, stderr = self.execute('ip -j addr list')

            addrs = json.loads(stdout)

            return addrs   
        except Exception as e:
            print(f"Exception: {e}")


    def get_paramiko_key(self, private_key_file=None, get_private_key_passphrase=None):
        #TODO: This is a bit of a hack and should probably test he keys for their types
        # rather than relying on execptions
        if get_private_key_passphrase:
            try:
                return paramiko.RSAKey.from_private_key_file(self.get_private_key_file(),  password=self.get_private_key_passphrase())
            except:
                pass
    
            try:
                return paramiko.ecdsakey.ECDSAKey.from_private_key_file(self.get_private_key_file(),  password=self.get_private_key_passphrase())
            except:
                pass
        else:
            try:
                return paramiko.RSAKey.from_private_key_file(self.get_private_key_file())
            except:
                pass
    
            try:
                return paramiko.ecdsakey.ECDSAKey.from_private_key_file(self.get_private_key_file())
            except:
                pass
    
        raise Exception(f"ssh key invalid: FABRIC requires RSA or ECDSA keys")


    def execute(self, command, retry=3, retry_interval=10, username=None, private_key_file=None, private_key_passphrase=None, chunking=False, quiet=True, read_timeout=10, timeout=None):
        """
        Runs a command on the FABRIC node.
        :param command: the command to run
        :type command: str
        :param retry: the number of times to retry SSH upon failure
        :type retry: int
        :param retry_interval: the number of seconds to wait before retrying SSH upon failure
        :type retry_interval: int
        :param chunking: enable reading stdout and stderr in real-time with chunks
        :type chunking: bool
        :param quiet: print stdout and stderr to the screen
        :type quiet: bool
        :param read_timeout: the number of seconds to wait before retrying to
        read from stdout and stderr
        :type read_timeout: int
        :param timeout: the number of seconds to wait before terminating the
        command using the linux timeout command. Specifying a timeout
        encapsulates the command with the timeout command for you
        :type timeout: int
        :return: a tuple of  (stdout[Sting],stderr[String])
        :rtype: Tuple
        :raise Exception: if management IP is invalid
        """
        import logging

        logging.debug(f"execute node: {self.get_name()}, management_ip: {self.get_management_ip()}, command: {command}")

        if not quiet:
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

        for attempt in range(retry):
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
                    if not quiet:
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
                                if not quiet:
                                    print(str(stdoutbytes,'utf-8').replace('\\n','\n'), end='')
                                stdout_chunks.append(stdoutbytes)
                                got_chunk = True
                            if c.recv_stderr_ready(): 
                                # make sure to read stderr to prevent stall
                                stderrbytes =  stderr.channel.recv_stderr(len(c.in_stderr_buffer))
                                if not quiet:
                                    print('\x1b[31m',str(stderrbytes,'utf-8').replace('\\n','\n'),'\x1b[0m', end='')
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

                return rtn_stdout, rtn_stderr
                #success, skip other tries
                break
            except Exception as e:
                print(e)
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


                if attempt+1 == retry:
                    raise e

                #Fail, try again
                if self.get_fablib_manager().get_log_level() == logging.DEBUG:
                    logging.debug(f"SSH execute fail. Slice: {self.get_slice().get_name()}, Node: {self.get_name()}, trying again")
                    logging.debug(e, exc_info=True)

                time.sleep(retry_interval)
                pass

        raise Exception("ssh failed: Should not get here")


    def show(self):
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

        

        
# Add methods to FABlib Classes
from fabrictestbed_extensions.fablib.node import Node

#fablib.Node
setattr(Node, 'show', Node_Custom.show)


setattr(Node, 'get_ip_routes', Node_Custom.get_ip_routes)
setattr(Node, 'get_ip_addrs', Node_Custom.get_ip_addrs)

setattr(Node, 'get_paramiko_key', Node_Custom.get_paramiko_key)
setattr(Node, 'execute', Node_Custom.execute)


