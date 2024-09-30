from plugins import Plugin
import argparse

class basic(Plugin):
    name = 'debug'
     
    def run(self, args):
        parser = argparse.ArgumentParser(prog='')
        parser.add_argument('-r', '--reload', action='store_true')
        functions = parser.parse_args(args)
        
        if functions.reload:
            self.paladin._load_plugins()
        #sys.__stdout__.write('\n\r')
        #return ''
        
    #def __init__(self, paladin):
    #    super().__init__(paladin)
    

    