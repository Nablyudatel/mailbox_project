from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase
from django.urls import reverse

from accounts.models import MailboxUser
from mail_box.models import Letter, EmailTypes


class BaseTest(TestCase):
    """Нужен для наследования, чтобы не повторять инициализацию"""
    fixtures = ["initial_data.json", ]

    def setUp(self) -> None:
        self._login_user("admin@mail.ru", "adminadmin")

    def _login_user(self, email, password):
        self.authorized_user = MailboxUser.objects.get(email="admin@mail.ru")
        result = self.client.login(email=self.authorized_user.email, password="adminadmin")
        self.assertTrue(result, "Пользователь не прошёл авторизацию")

    def _unauthorized_login_attempt_to_view_authorize_required(self, url):
        """
        Нужна для проверки представлений для которых требуется авторизация
        """

        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        redirect_url_without_parameters = response.url.split("?")[0] if "?" in response.url else response.url
        self.assertEqual(redirect_url_without_parameters, reverse("login"))


class TestOfPages(BaseTest):
    """Не стал делать по отдельным классам эти страницы так-как проверок пока мало"""

    def test_login(self):
        """Проверяет сессию пользователя на наличие авторизации в системе"""
        self.assertTrue(self.authorized_user.is_authenticated)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.authorized_user.pk)

    def test_main_page(self):
        response = self.client.get(reverse("main_page"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main_page.html")

    def test_letter_page(self):
        """Страница с отображением письма"""

        # попытка прочитать своё письмо
        # этот запрос чтобы обязательно были непрочитанные письма у пользователя
        Letter.objects.filter(user=self.authorized_user, is_read=True).update(is_read=False)

        letter_of_user = Letter.objects.filter(user=self.authorized_user).earliest("id")
        self.assertFalse(letter_of_user.is_read)
        response = self.client.get(
            reverse("letter_page",
                    kwargs={"letter_id": letter_of_user.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mail_box/letter_page.html")
        letter_in_context = response.context["letter"]
        self.assertTrue(letter_in_context.is_read)

        # попытка прочитать чужое письмо
        response = self.client.get(
            reverse("letter_page",
                    kwargs={"letter_id": Letter.objects.exclude(user=self.authorized_user).earliest("id").id})
        )
        self.assertEqual(response.status_code, 403)

        # Попытка прочитать письмо неавторизованным
        self._unauthorized_login_attempt_to_view_authorize_required(
            reverse("letter_page", kwargs={"letter_id": letter_of_user.id}))

    def test_inbox_page(self):
        # Вход на свою страницу со входящими
        response = self.client.get(reverse("inbox_page"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mail_box/inbox.html")

        # Проверка контекста шаблона на наличие писем
        self.assertTrue(response.context.get("letters"))
        inbox_letters = Letter.objects.filter(user=self.authorized_user, type=EmailTypes.INCOMING.value).order_by("-id")
        # список входящих соотвестствует списку входящих в контексте шаблона
        self.assertListEqual(list(response.context["letters"]), list(inbox_letters))

        # Попытка зайти на страницу неавторизованным
        self._unauthorized_login_attempt_to_view_authorize_required(reverse("inbox_page"))

    def test_sent_page(self):
        response = self.client.get(reverse("sent_page"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mail_box/sent.html")

        # Проверка контекста шаблона на наличие писем
        self.assertTrue(response.context.get("letters"))
        sent_letters = Letter.objects.filter(user=self.authorized_user, type=EmailTypes.OUTGOING.value).order_by("-id")
        # список входящих соотвестствует списку входящих в контексте шаблона
        self.assertListEqual(list(response.context["letters"]), list(sent_letters))

        # Попытка зайти на страницу неавторизованным
        self._unauthorized_login_attempt_to_view_authorize_required(reverse("sent_page"))

    def test_send_email_get_page(self):
        """Тест страницы создания письма, на которую разрешён только гет-запрос"""
        response = self.client.get(reverse("send_email_page"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mail_box/send_email_page.html")

        # Попытка зайти на страницу неавторизованным
        self._unauthorized_login_attempt_to_view_authorize_required(reverse("send_email_page"))

    def test_send_email_post_page(self):
        """Тест страницы повторного редактирования письма, на которую разрешён только пост-запрос"""

        # гет-запрос не должен пройти
        response = self.client.get(reverse("send_email"))
        self.assertEqual(response.status_code, 405)

        # запрос на отправку пиьсма, пока без содержимого
        response = self.client.post(reverse("send_email"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mail_box/send_email_page.html")


class TestDeleteLetter(BaseTest):

    def _is_letter_deleted(self, letter_id):
        with self.assertRaises(Letter.DoesNotExist):
            self.authorized_user.letters_set.get(id=letter_id)

    def test_delete_sent_email(self):
        # удаление письма из отправленных
        letter_id = self.authorized_user.letters_set.filter(type=EmailTypes.OUTGOING.value).earliest("id").id
        response = self.client.get(reverse("delete_letter", kwargs={"letter_id": letter_id}))
        self.assertRedirects(response, reverse("sent_page"))
        self._is_letter_deleted(letter_id)

    def test_delete_incoming_letter(self):
        # удаление письма из входящих
        letter_id = self.authorized_user.letters_set.filter(type=EmailTypes.INCOMING.value).earliest("id").id
        response = self.client.get(reverse("delete_letter", kwargs={"letter_id": letter_id}))
        self.assertRedirects(response, reverse("inbox_page"))
        self._is_letter_deleted(letter_id)

    def test_attempt_delete_another_user_letter(self):
        """Попытка удалить чужое письмо"""
        letter_id = Letter.objects\
            .filter(type=EmailTypes.INCOMING.value)\
            .exclude(user=self.authorized_user)\
            .earliest("id").id
        response = self.client.get(reverse("delete_letter", kwargs={"letter_id": letter_id}))
        self.assertEqual(response.status_code, 403)

    def test_unauthorized_login(self):
        self._unauthorized_login_attempt_to_view_authorize_required(
            reverse("delete_letter", kwargs={"letter_id": 1}))


class TestSendEmails(TestCase):
    fixtures = ["initial_data.json", ]

    def setUp(self) -> None:
        self.target_users = list(MailboxUser.objects.all()[1:3])
        self.sender = MailboxUser.objects.all()[0]

    def _checked_created_emails(self, sender, target_users, letters):
        self.assertEqual(len(letters), 3)
        for letter in letters:
            if letter.get_type() is EmailTypes.INCOMING:
                self.assertIn(letter.user, target_users)
                self.assertFalse(letter.is_read)
            elif letter.get_type() is EmailTypes.OUTGOING:
                self.assertEqual(letter.user, sender)
                self.assertTrue(letter.is_read)
            else:
                self.fail()

    def test_send_valid_data(self):
        """Отправка письма с валидными данными"""

        header = "Тестовое письмо номер один",
        text = "Какой-то дурацкий текст."

        letters = self.sender.send_mail(header, text, self.target_users)
        self._checked_created_emails(self.sender, self.target_users, letters)

    def test_send_invalid_header(self):

        # слишком длинный заголовок
        header = "".join("s" for _ in range(75))
        text = "Какой-то дурацкий текст."
        with self.assertRaises(ValidationError):
            self.sender.send_mail(header, text, self.target_users)

        # осутствие заголовка
        header = ""
        text = "Какой-то дурацкий текст."
        with self.assertRaises(ValidationError):
            self.sender.send_mail(header, text, self.target_users)

    def test_send_invalid_text(self):

        # слишком длинный текст
        header = "Заголовок"
        text = "".join("s" for _ in range(901))
        with self.assertRaises(ValidationError):
            self.sender.send_mail(header, text, self.target_users)

        # осутствие текста
        header = "Заголовок"
        text = ""
        with self.assertRaises(ValidationError):
            self.sender.send_mail(header, text, self.target_users)

    def test_read_user_letter(self):
        user = MailboxUser.objects.all().earliest("id")
        Letter.objects.filter(user=user, is_read=True).update(is_read=False)
        letter_of_user = Letter.objects.filter(user=user).earliest("id")
        user.read_letter(letter_of_user)
        self.assertTrue(letter_of_user.is_read)

    def test_read_another_user_letter(self):
        user = MailboxUser.objects.all().earliest("id")
        another_of_user_letter = Letter.objects.exclude(user=user, is_read=False).earliest("id")
        with self.assertRaises(PermissionDenied):
            user.read_letter(another_of_user_letter)


class TestSendEmailsFromViews(BaseTest):

    def test_send_valid_data(self):
        """запрос на отправку письма с валидными данными"""

        total_letters = Letter.objects.count()
        # Так как письмо отправляется трём пользователям, то в базе должно быт не меньше трёх.
        self.assertTrue(MailboxUser.objects.count() >= 3)

        # Первые три пользователя, которым должны прийти письма
        target_users = MailboxUser.objects.all()[:2]
        inbox_mail_count_list = [u.letters_set.filter(type=EmailTypes.INCOMING.value).count() for u in target_users]
        sent_mail_count_of_sender = self.authorized_user.letters_set.filter(type=EmailTypes.OUTGOING.value).count()

        mail_data = {
            "addressee": [1, 2, 3],
            "header": "Тестовое письмо номер один",
            "text": "Какой-то дурацкий текст."
        }

        response = self.client.post(reverse("send_email"), data=mail_data)

        # после успешной отправки происходит редирект на главную
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("main_page"))

        # Должно появиться четыре письма. Одно исходящее и три входящих
        self.assertEqual(total_letters + 4, Letter.objects.count())

        # у каждого адресата должно появиться по одному входящему
        new_inbox_mail_count_list = [u.letters_set.filter(type=EmailTypes.INCOMING.value).count() for u in target_users]
        for v in inbox_mail_count_list:
            for new_v in new_inbox_mail_count_list:
                self.assertEqual(v + 1, new_v)

        # у отправителья должно появиться одно исходящее письмо
        current_sent_mail_count = self.authorized_user.letters_set.filter(type=EmailTypes.OUTGOING.value).count()
        self.assertEqual(sent_mail_count_of_sender + 1, current_sent_mail_count)

    def test_send_invalid_addressee_data(self):

        # Ни один пользователь не был указан получателем письма
        mail_data = {
            "addressee": [],
            "header": "Тестовое письмо номер один",
            "text": "Какой-то дурацкий текст."
        }

        response = self.client.post(reverse("send_email"), data=mail_data)

        # происходить возврат на страницу для дальнейшего редактирования письма
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mail_box/send_email_page.html")

        # несуществующие в базе пользователи
        mail_data = {
            "addressee": [5, 6, 7],
            "header": "Тестовое письмо номер один",
            "text": "Какой-то дурацкий текст."
        }

        response = self.client.post(reverse("send_email"), data=mail_data)
        self.assertEqual(response.status_code, 200)

    def test_send_invalid_header(self):
        # Слишком длинный заголовок
        mail_data = {
            "addressee": [1, 2, 3],
            "header": "".join("s" for _ in range(71)),
            "text": "Какой-то дурацкий текст."
        }
        response = self.client.post(reverse("send_email"), data=mail_data)
        self.assertEqual(response.status_code, 200)

        # Отстутствие заголовка
        mail_data = {
            "addressee": [1, 2, 3],
            "header": "",
            "text": "Какой-то дурацкий текст."
        }
        response = self.client.post(reverse("send_email"), data=mail_data)
        self.assertEqual(response.status_code, 200)

    def test_send_invalid_text(self):

        # Слишком длинный текст
        mail_data = {
            "addressee": [1, 2, 3],
            "header": "Заголовок",
            "text": "".join("s" for _ in range(902)),
        }

        response = self.client.post(reverse("send_email"), data=mail_data)
        self.assertEqual(response.status_code, 200)

        # Отсутствие текста
        mail_data = {
            "addressee": [1, 2, 3],
            "header": "Заголовок",
            "text": "",
        }

        response = self.client.post(reverse("send_email"), data=mail_data)
        self.assertEqual(response.status_code, 200)
