from django.urls import path, include

from accounts.views import sign_up_page

urlpatterns = [
    path("sign-up/", sign_up_page, name="sign_up_page"),
    path("", include('django.contrib.auth.urls')),
]