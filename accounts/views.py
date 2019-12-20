from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST


def create_user(request):
    user_creation_form = UserCreationForm(request.POST)
    if user_creation_form.is_valid():
        user_creation_form.save()
        response = ...
    else:
        response = ...
    return response


@require_GET
@csrf_protect
def login_page(request):
    ...


@require_POST
def login_user(request):
    authenticate()