from plugins import Plugin

class Spyglass(Plugin):
    name = 'spyglass'

    def __init__(self, paladin):
        super().__init__(paladin)
    
    def run(self, args):
        print(args.split())
        for arg in args.split():
            try:
                print(self.paladin.__getattribute__(arg))
            except:
                print(f'No attribute named {arg}')