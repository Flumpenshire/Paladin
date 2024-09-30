from typing import Callable
class Plugin():
    '''The base Paladin module. This contains the necessary methods to load into the command interpreter. The parent is saved to access it's data.
    Set self.run with the main function of the script.
    set self.name with a command friendly name.'''
    run : Callable
    
    
    def __init__(self, paladin):
        self.paladin = paladin
        self.paladin.plugins[self.name] = self.run
        