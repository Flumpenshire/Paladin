from plugins import Plugin
import argparse

class sftp(Plugin):
    name = 'sftp'
    
    def run(self, args):
        parser = argparse.ArgumentParser(prog='')

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-u', '--upload', action='store_true')
        group.add_argument('-d', '--download', action='store_true')

        parser.add_argument('file')
        parser.add_argument('-o', '--output', required=False)

        args = parser.parse_args(args)
        
        path = self.paladin.get_path()

        try:
            if args.upload:
                if not args.output:
                    args.output = f'{path}/{args.file}'

                else:
                    self.paladin.client.copy_file(args.file, args.output)
        
            if args.download:
                if not args.output:
                    args.output = args.file
                
                self.paladin.client.scp_recv(f'{path}/{args.file}', args.output)
                self.paladin.printout('Download complete!')


        except Exception as e:
            self.paladin.printout(f'{e.args[1]} was not found!')
            return ''

        


    