from django.contrib.auth.tokens import PasswordResetTokenGenerator

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Use user's primary key, timestamp, and activation status
        return str(user.pk) + str(timestamp) + str(user.is_active)

# Create the token instance
account_activation_token = AccountActivationTokenGenerator()
