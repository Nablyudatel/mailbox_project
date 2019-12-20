from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect

from accounts.forms import MailboxUserCreationForm


def sign_up_page(request):
    """Страница регистрации пользователя"""

    if request.method == "POST":
        form = MailboxUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=True)
            messages.success(request, "Поздравляем с успешной регистрацией!!!")
            login(request, user=user)
            response = redirect("main_page")
        else:
            # Возвращение на страницу с сохранением данных ввода
            response = render(request, "registration/sign_up.html", {"form": form})
    elif request.method == "GET":
        form = MailboxUserCreationForm()
        response = render(request, "registration/sign_up.html", {"form": form})
    else:
        raise RuntimeError()
    return response
