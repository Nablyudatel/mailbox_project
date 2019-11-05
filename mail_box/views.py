from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_GET

from mail_box.forms import EmailForm
from .models import Letter, EmailTypes, MailboxUser


@require_GET
@login_required
def main_page(request):
    user = request.user
    total_new_letters = Letter.objects.filter(user=user, type=EmailTypes.INBOX.value, is_read=False).count()
    return render(request, "main_page.html", {"total_new_letters": total_new_letters})


@require_GET
@login_required
def inbox(request):
    user = request.user
    letters = Letter.objects.filter(user=user, type=EmailTypes.INBOX.value)
    return render(request, "inbox.html", {"letters": letters})


@require_GET
@login_required
def sent_box(request):
    user = request.user
    letters = Letter.objects.filter(user=user, type=EmailTypes.SENT.value)
    return render(request, "sent.html", {"letters": letters})


@require_GET
@login_required
@csrf_protect
def send_email_page(request):
    email_form = EmailForm()
    return render(request, "send_email_page.html", {"email_form": email_form})


@require_POST
@login_required
@csrf_protect
def send_email(request):
    user: "MailboxUser" = request.user.mailboxuser
    email_form = EmailForm(request.POST)
    if email_form.is_valid():
        header = email_form.cleaned_data["header"]
        text = email_form.cleaned_data["text"]
        users = email_form.cleaned_data["addressee"]
        user.send_mail(header, text, users)
        response = redirect("main_page")
    else:
        response = render(request, "send_email_page.html", {"email_form": email_form})
    return response


@require_GET
@login_required
def letter_page(request, letter_id):
    user: "MailboxUser" = request.user.mailboxuser
    letter = get_object_or_404(Letter, id=letter_id)

    if not user.is_ownership_letter(letter):
        raise PermissionDenied()

    letter.is_read = True
    letter.save()

    return render(request, "letter_page.html", {"letter": letter})
