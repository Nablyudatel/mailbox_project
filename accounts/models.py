from typing import List

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction


class MailboxUserManager(BaseUserManager):
    """
    Переопределённый менеджер мользователя.
    Нужен чтобы переопределить сигнатуры создания различных пользователей.
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class MailboxUser(AbstractUser):
    """
    Пользователь почтового ящика
    Переопределён чтобы можно было его расширять.

    По сравнению с дефолтным, было убрано поле username,
    и добавлена возможность авторизации по названию почтового ящика.
    """

    objects = MailboxUserManager()

    email = models.EmailField(unique=True)
    username = None  # поле родительской модели переопределено за ненадобностью

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ()

    def __str__(self):
        return f"{self.first_name} {self.last_name}: [{self.email}]"

    @transaction.atomic
    def send_mail(self, header: "str", text: "str", users: "List[MailboxUser]") -> "List[Letter]":
        """
        Метод отправки писем, и по-сути их конструктор.
        Дело в том, что письмо по-сути отправляется путём его создания.
        """

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


# импорт размещён здесь намеренно.
# Чтобы работали аннотации и не сооздавался повод для появления циклической зависимости
from mail_box.models import Message, Letter, EmailTypes
