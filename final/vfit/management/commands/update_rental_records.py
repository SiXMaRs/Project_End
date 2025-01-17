from django.core.management.base import BaseCommand
from vfit.models import RentalRecord

class Command(BaseCommand):
    help = 'Update rental records time remaining and overdue time'

    def handle(self, *args, **kwargs):
        rentals = RentalRecord.objects.filter(status__in=['renting', 'overdue'])
        for rental in rentals:
            rental.update_time_status()
        self.stdout.write(self.style.SUCCESS('Successfully updated rental records.'))
