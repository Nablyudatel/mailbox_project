from django.contrib import admin

# Register your models here.
from accounts.models import MailboxUser


@admin.register(MailboxUser)
class MailboxUserAdmin(admin.ModelAdmin):
    pass
