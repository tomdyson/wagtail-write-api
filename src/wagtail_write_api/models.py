import secrets

from django.conf import settings
from django.db import models


class ApiToken(models.Model):
    key = models.CharField(max_length=40, primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="wagtail_write_api_token",
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "API token"
        verbose_name_plural = "API tokens"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
            if self._state.adding:
                kwargs["force_insert"] = True
        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls):
        return secrets.token_hex(20)

    def __str__(self):
        return self.key
