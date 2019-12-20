from django.contrib.auth.forms import UserCreationForm

from accounts.models import MailboxUser


class MailboxUserCreationForm(UserCreationForm):
    """
    Переопределил модель формы на модель проекта,
    затратив таким образом минимум работы на новую.
    """

    class Meta:
        model = MailboxUser
        fields = ("email", "first_name", "last_name")
