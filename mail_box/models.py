from enum import Enum
from typing import List

from django.contrib.auth.models import User
from django.db import models, transaction


class EmailTypes(Enum):
    INBOX = "ВХД"
    SENT = "ИСХ"


class MailboxUser(User):
    email_address = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}: [{self.email_address}]"

    @transaction.atomic
    def send_mail(self, header: "str", text: "str", users: "List[MailboxUser]") -> "List[Letter]":
        """Метод отправки писем, и по-сути их конструктор."""
        message = Message.objects.create(sender=self, header=header, text=text)
        message.addressees_set.add(*users)
        sent_email = Letter(user=self, message=message, type=EmailTypes.SENT.value)

        emails = [sent_email, ]
        for user in users:  # type: MailboxUser
            inbox_email = Letter(user=user, message=message, type=EmailTypes.INBOX.value, is_read=False)
            emails.append(inbox_email)
        emails = Letter.objects.bulk_create(emails)  # Чтобы одним запросом все письма сохранить.
        return emails

    def is_ownership_letter(self, letter: "Letter"):
        return letter.user == self


class Message(models.Model):
    addressees_set = models.ManyToManyField(MailboxUser, related_name="incoming_messages_set")
    sender = models.ForeignKey(MailboxUser, on_delete=models.PROTECT, related_name="sent_messages_set")
    header = models.CharField(max_length=300)
    text = models.TextField(max_length=2000)


class Letter(models.Model):
    user = models.ForeignKey(MailboxUser, on_delete=models.CASCADE, related_name="letters_set")
    message = models.ForeignKey("Message", on_delete=models.PROTECT, related_name="+")
    type = models.CharField(max_length=4, choices=[(code.name, code.value) for code in EmailTypes])
    is_read = models.BooleanField(default=True)
