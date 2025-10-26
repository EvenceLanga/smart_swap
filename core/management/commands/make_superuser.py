from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Promote a user to superuser'

    def handle(self, *args, **kwargs):
        user = User.objects.get(username='evencemohaulanga') 
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f'{user.username} is now a superuser!'))
