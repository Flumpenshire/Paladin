#!/usr/bin/env python3
from pssh.clients import SSHClient
import pssh.exceptions
import simple_plugin_loader

from plugins import Plugin

import threading
import pty
import os, sys
import configparser
import argparse
import getpass
import subprocess



class Paladin(): 
    PALADIN_PATH = os.path.dirname(os.path.realpath(__file__))

    def __init__(self, config_file = None):
        self._parse_arguements()
        self._load_config(config_file)
        self._load_plugins()

        # These values are named from the remote host perspective
        self.SEND_FILE = f'{self.remote_directory}/recv.fifo'
        self.RECV_FILE = f'{self.remote_directory}/send.fifo'
        self.COMM_FILE = f'{self.remote_directory}/comm.fifo'

        self.THREADS_OPEN = True
        self.commands = []
        self.command_available = threading.Event()

    def _load_plugins(self):
        self.plugins = {}
        loader = simple_plugin_loader.Loader()
        plugins = loader.load_plugins(f"{self.PALADIN_PATH}/plugins", Plugin)
        for plugin in plugins.values():
            plugin(self)

    def _parse_arguements(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('host')
        parser.add_argument('-p', '--port')
        parser.add_argument('-i')

        args = parser.parse_args()

        split= args.host.find('@')
        if split != -1:
            self.user = args.host[:split]
            self.host = args.host[split+1:]
        else:
            self.user = os.environ.get('USER', os.environ.get('USERNAME'))
            self.host = args.host

        if args.port:
            self.port = args.port
        else:
            self.port = 22

        if args.i:
            self.key = args.i

    def _load_config(self, config_file):
        config = configparser.SafeConfigParser(interpolation=configparser.BasicInterpolation())
        if not config_file:
            config.read(f'{self.PALADIN_PATH}/paladin.cfg')

        self.prefix = config['DEFAULT']['prefix']
        self.remote_directory = config['DEFAULT']['remote_directory']
        self.private_key = config['AUTHENTICATION']['private_key']
        self.public_key = config['AUTHENTICATION']['public_key']

    def _get_motd(self, COMMAND):
        # The extra sting below fails all authentication attemps and will return the banner and a failure line. We can remove the failure line to get only the banner.
        proc = subprocess.run(' '.join(COMMAND) + " -T -o PubkeyAuthentication=no -o PasswordAuthentication=no", text=True, timeout=1, shell=True, capture_output=True)
        motd = proc.stderr.splitlines()[:-1]

        self.motd = motd
        
    def _try_login(self):
        fails = 0
        while fails !=3:
            try:
                self.password = getpass.getpass(f"{''.join(self.motd)}\n{self.user}@{self.host}'s password:")
                self.client = SSHClient(self.host, self.user, self.password, self.port, identity_auth=False, timeout=3, retry_delay=0, num_retries=0)
                return True
            
            except pssh.exceptions.Timeout as e:
                self.printout('Your connection timed out. Paladin only handles 3 seconds of delay currently.')
                return False
            
            except pssh.exceptions.AuthenticationError as e:
                self.printout('Login failed.')
                fails +=1
                if fails == 3:
                    return False
        
    def _inject_key(self):
        #For the LIFE of me, I don't know why it's not working outside of authorized keys. We're just going to use an overly specific SED command.
        with open(self.public_key, 'r') as key:
            data = key.readline().strip('\n')
        self.client.run_command(f"echo '{data} # paladin identifier code' >> ~/.ssh/authorized_keys")
        #RSA file messes this up.
        self.client.run_command(f"sleep 5 && sed -i '/paladin identifier code/d' ~/.ssh/authorized_keys")

    def _create_tmp(self):
        self.client.run_command(f'mkdir {self.remote_directory}')
        self.client.copy_file("paladin.sh", f"{self.remote_directory}/paladin")
        self.client.run_command(f'chmod +x {self.remote_directory}/paladin')
        self.client.run_command(f'echo "export PATH=$PATH:{self.remote_directory}" >> ~/.bashrc')
        self.client.run_command(f"sleep 5 && sed -i '/.paladin/d' ~/.bashrc")

        self.client.run_command(f'mkfifo {self.SEND_FILE}')
        self.client.run_command(f'mkfifo {self.RECV_FILE}')
        self.client.run_command(f'mkfifo {self.COMM_FILE}')

    def _command_watcher(self):
        self._create_tmp()

        self.command_watcher = self.client.run_command(f'tail -f {self.RECV_FILE}')
        for command in self.command_watcher.stdout:
            self.commands.append(command)
            self.command_available.set()
            
    def _start_command_watcher(self):
        self.thread = threading.Thread(target=self._command_watcher, daemon=True)
        self.thread.start()

    def _command_executor(self):
        while self.THREADS_OPEN:
            self.command_available.wait()
            try:
                command = self.commands.pop(0)
                command = command.split()
                response = self.plugins[command[0]](command[1:])
                if not response:
                    response = ''
                self.client.run_command(f"echo '{response}' > {self.SEND_FILE}")
                if len(self.commands) == 0:
                    self.command_available.clear()
            except Exception as e:
                print(e)
                self.command_available.clear()

    def _start_command_executor(self):
        self.thread = threading.Thread(target=self._command_executor, daemon=True)
        self.thread.start()

    def create_client(self):
        COMMAND = ['/usr/bin/ssh', f'-i{self.private_key}', f'{self.user}@{self.host}', f'-p {self.port}', '-o StrictHostKeyChecking=accept-new']
        self._get_motd(COMMAND)
        if not self._try_login():
            self.printout('Max retries exceeded.')
            exit()
            
        self._inject_key()
        self._start_command_watcher()
        self._start_command_executor()

        pty.spawn(COMMAND)

        self.THREADS_OPEN = False
        self.client.run_command(f'rm -rf {self.remote_directory}')

    # Useful functions for scripts.
    @staticmethod
    def printout(string):
        sys.__stdout__.write(string + '\n\r')
    
    def get_path(self, final = True) -> str:
        '''Returns the client terminal's current path. By default, this ends the command reception in the terminal.
        Setting final to False will leave the SEND_FILE open for new commands.'''
        if final:
            self.client.run_command(f'echo "pwd 1> {self.COMM_FILE}; bash {self.SEND_FILE}" > {self.SEND_FILE}')
        else:
            self.client.run_command(f'echo "pwd >> {self.COMM_FILE}" > {self.SEND_FILE}')
        comm = self.client.run_command(f'cat {self.COMM_FILE}')
        
        path = ''.join(line for line in comm.stdout)
        return path



if __name__ == '__main__':
    container = Paladin()
    container.create_client()
