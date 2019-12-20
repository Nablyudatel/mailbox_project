from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_GET

from mail_box.forms import EmailForm
from .models import Letter, EmailTypes
from accounts.models import MailboxUser


@require_GET
def main_page(request):
    """Главная страница"""
    user = request.user
    if user.is_authenticated:
        total_new_letters = Letter.objects.filter(user=user, type=EmailTypes.INBOX.value, is_read=False).count()
    else:
        total_new_letters = []
    return render(request, "main_page.html", {"total_new_letters": total_new_letters})


@require_GET
@login_required
def inbox(request):
    """Ящик входящей почты"""
    user = request.user
    letters = Letter.objects.filter(user=user, type=EmailTypes.INBOX.value)
    return render(request, "mail_box/inbox.html", {"letters": letters})


@require_GET
@login_required
def sent_box(request):
    """Ящик исходящей почты"""
    user = request.user
    letters = Letter.objects.filter(user=user, type=EmailTypes.SENT.value)
    return render(request, "mail_box/sent.html", {"letters": letters})


@require_GET
@login_required
@csrf_protect
def send_email_page(request, email_form=None):
    """
    Страница с формой отправки письма.
    Отображается при гет-запросе.
    """
    email_form = email_form if email_form else EmailForm()
    return render(request, "mail_box/send_email_page.html", {"email_form": email_form})


@require_POST
@login_required
@csrf_protect
def send_email(request):
    """
    Представление для отправки письма.
    При неверных данных возвращает на страницу отправки письма,
    сохраняя введённые данные.
    """

    # noinspection PyTypeChecker
    user: "MailboxUser" = request.user
    email_form = EmailForm(request.POST)
    if email_form.is_valid():
        header = email_form.cleaned_data["header"]
        text = email_form.cleaned_data["text"]
        users = email_form.cleaned_data["addressee"]
        user.send_mail(header, text, users)
        response = redirect("main_page")
        messages.success(request, "Письмо успешно отправлено.")
    else:
        response = render(request, "mail_box/send_email_page.html", {"email_form": email_form})
    return response


@require_GET
@login_required
def letter_page(request, letter_id):
    """Страница для просмотра содержимого письма."""

    # noinspection PyTypeChecker
    user: "MailboxUser" = request.user
    letter = get_object_or_404(Letter, id=letter_id)

    if not user.is_ownership_letter(letter):
        raise PermissionDenied()

    letter.is_read = True
    letter.save()

    return render(request, "mail_box/letter_page.html", {"letter": letter})
