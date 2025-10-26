from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Promote one or more users to superuser'

    def handle(self, *args, **kwargs):
        # 🧑‍💻 List all usernames you want to promote
        usernames = ['evencemohaulanga', 'Busiswe_Buthelezi']

        for username in usernames:
            try:
                user = User.objects.get(username=username)
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'{username} is now a superuser!'))
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'User "{username}" not found!'))
