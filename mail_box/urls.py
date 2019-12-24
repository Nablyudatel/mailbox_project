from django.urls import path

from mail_box.views import inbox, sent_box, send_email, send_email_page, letter_page, delete_letter

urlpatterns = [
    path("inbox/", inbox, name="inbox_page"),
    path("sent/", sent_box, name="sent_page"),
    path("send-email-page/", send_email_page, name="send_email_page"),
    path("send-email/", send_email, name="send_email"),
    path("letter/letter_id-<int:letter_id>/", letter_page, name="letter_page"),
    path("letter/delete/letter_id-<int:letter_id>/", delete_letter, name="delete_letter")
]