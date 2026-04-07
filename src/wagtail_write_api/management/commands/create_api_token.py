from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from wagtail_write_api.models import ApiToken


class Command(BaseCommand):
    help = "Create or retrieve an API token for a user"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing token and create a new one",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: options["username"]})
        except User.DoesNotExist:
            raise CommandError(f"User '{options['username']}' does not exist")

        if options["reset"]:
            ApiToken.objects.filter(user=user).delete()

        token, created = ApiToken.objects.get_or_create(user=user)
        if created:
            self.stdout.write(f"Created token: {token.key}")
        else:
            self.stdout.write(f"Token: {token.key}")
