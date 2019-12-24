from enum import Enum

from django.contrib.auth.models import AbstractUser
from django.db import models

from mailbox_project import settings


class EmailTypes(Enum):
    INCOMING = "ВХД"
    OUTGOING = "ИСХ"

    @classmethod
    def str_to_constant(cls, string: str):
        for const in cls:
            if const.value == string:
                return const
        else:
            raise RuntimeError()


class Message(models.Model):
    """Содержимое письма"""

    # Адресатов можно находить динамически, по письмам привязанным к сообщению
    # но это сложные запросы, поэтому решил, что лучше хранить в поле сообщения addressees_set.
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
    type = models.CharField(max_length=3, choices=[(code.value, code.name) for code in EmailTypes])
    is_read = models.BooleanField(default=True)

    def get_type(self) -> "EmailTypes":
        return EmailTypes.str_to_constant(self.type)
