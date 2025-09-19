from django.core.management.base import BaseCommand
from fitbit.analyzer import run_fitbit_analysis
from fitbit.ai_helper import generate_analysis
from fitbit.teams_notifier import send_message
import os


class Command(BaseCommand):
    help = 'Run Fitbit module analysis and notify partners via Teams (stub)'

    def add_arguments(self, parser):
        parser.add_argument('--webhook', help='Teams webhook URL to send messages', default=os.environ.get('TEAMS_WEBHOOK_URL'))

    def handle(self, *args, **options):
        webhook = options.get('webhook')
        comparison = run_fitbit_analysis()
        for partner, comp in comparison.items():
            analysis = generate_analysis(partner, comp)
            title = f'Fitbit Analysis - {partner}'
            text = analysis['summary'] + '\n\nRecommendation:\n' + analysis['suggestion']
            res = send_message(webhook, title, text)
            self.stdout.write(self.style.SUCCESS(f'Sent to {partner}: {res}'))
