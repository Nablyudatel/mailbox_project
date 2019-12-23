from enum import Enum

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxLengthValidator
from django.db import models

from mailbox_project import settings


class EmailTypes(Enum):
    INBOX = "ВХД"
    SENT = "ИСХ"

    @classmethod
    def str_to_constant(cls, string: str):
        for const in cls:
            if const.value == string:
                return const
        else:
            raise RuntimeError()


class Message(models.Model):
    """Содержимое письма"""

    addressees_set = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="incoming_messages_set")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sent_messages_set")
    header = models.CharField(max_length=70)
    text = models.CharField(max_length=900)


class Letter(models.Model):
    """
    Само письмо.
    Если пользователь разослал письма десяти адресатам, то у каждого письма
    будет свой владелец, однако ссылаться все письма будут на одно содрежимое.

    Это необходимо во-первых для нормализации БД, а во-вторых позволит избежать ошибок
    связанных с удалением пользователей и удалением ими писем.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="letters_set")
    message = models.ForeignKey("Message", on_delete=models.PROTECT, related_name="+")
    type = models.CharField(max_length=5, choices=[(code.name, code.value) for code in EmailTypes])
    is_read = models.BooleanField(default=True)

    def get_type(self) -> "EmailTypes":
        return EmailTypes.str_to_constant(self.type)