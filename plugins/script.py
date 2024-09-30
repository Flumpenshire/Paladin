from plugins import Plugin
import configparser
import os
import argparse
import sys

class Script(Plugin):
    name = 'script'

    def __init__(self, paladin):
        super().__init__(paladin)
        self._startup()

    
    def run(self, args):
        parser = argparse.ArgumentParser(prog='')
        parser.add_argument('file')
        args = parser.parse_args(args)

        self.paladin.client.copy_file(f'{self.path}/{args.file}', f'{self.paladin.remote_directory}/{args.file}')
        #self.paladin.client.run_command(f'chmod +x ')
        #self.paladin.run_on_main(f' bash {self.paladin.remote_directory}/{args.file}')
        return f'bash {self.paladin.remote_directory}/{args.file}'

    def _startup(self):
        config = configparser.ConfigParser()
        config.read('plugins/configs/script.cfg')
        self.path = config['DEFAULT']['script_path']
        self.debug = config['DEFAULT']['debug']

        if self.debug:
            scripts = [script for script in os.scandir(self.path)]
            if len(scripts) == 0:
                self.paladin.printout('No scripts found.')
            else:
                for script in scripts:
                    self.paladin.printout(str(script))