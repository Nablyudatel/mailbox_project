from django import forms

from accounts.models import MailboxUser


class EmailForm(forms.Form):
    """
    Форма письма. Используется для отправки(создания писем)
    Чтобы пользователю было удобнее отправлять (нам же не нужна реалистичность?),
    сделал выбор из существующих в бд пользователей,
    как будто они у него находятся в контактах.
    """

    addressee = forms.ModelMultipleChoiceField(queryset=MailboxUser.objects.all(), label="Адресаты")
    header = forms.CharField(max_length=70, label="Заголовок")
    text = forms.CharField(max_length=900, widget=forms.Textarea, label="Текст")
