"""
Custom runserver command that defaults to port 8001

This command ensures that the Django development server always runs on port 8001
to match the configuration in launch_dashboard.py
"""

from django.core.management.commands.runserver import Command as RunserverCommand
from django.conf import settings


class Command(RunserverCommand):
    help = 'Starts the EY Dashboard development server on port 8001 (default)'
    
    def add_arguments(self, parser):
        super().add_arguments(parser)
        # Override the default port
        parser.set_defaults(addrport='127.0.0.1:8001')
    
    def handle(self, *args, **options):
        # If no specific address:port provided, use our default
        if not options.get('addrport'):
            options['addrport'] = '127.0.0.1:8001'
        elif ':' not in str(options['addrport']):
            # If only port number provided, ensure it's 8001
            try:
                port = int(options['addrport'])
                if port != 8001:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Warning: Using port {port} instead of required port 8001. '
                            f'The launcher expects port 8001.'
                        )
                    )
            except ValueError:
                pass
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting EY Dashboard server on {options["addrport"]}...'
            )
        )
        
        super().handle(*args, **options)
