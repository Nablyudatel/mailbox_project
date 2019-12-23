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
        authorize_required: bool = True  # предполагается проверять

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
        letter_of_user = Letter.objects.filter(user=self.authorized_user).earliest("id")
        response = self.client.get(
            reverse("letter_page",
                    kwargs={"letter_id": letter_of_user.id})
        )
        self.assertTemplateUsed(response, "mail_box/letter_page.html")

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
        inbox_letters = Letter.objects.filter(user=self.authorized_user, type=EmailTypes.INBOX.value)
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
        sent_letters = Letter.objects.filter(user=self.authorized_user, type=EmailTypes.SENT.value)
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


class TestSendEmailsFromViews(BaseTest):

    def test_send_valid_data(self):
        """запрос на отправку письма с валидными данными"""

        total_letters = Letter.objects.count()
        # Так как письмо отправляется трём пользователям, то в базе должно быт не меньше трёх.
        self.assertTrue(MailboxUser.objects.count() >= 3)

        # Первые три пользователя, которым должны прийти письма
        target_users = MailboxUser.objects.all()[:2]
        inbox_mail_count_list = [u.letters_set.filter(type=EmailTypes.INBOX.value).count() for u in target_users]
        sent_mail_count_of_sender = self.authorized_user.letters_set.filter(type=EmailTypes.SENT.value).count()

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
        new_inbox_mail_count_list = [u.letters_set.filter(type=EmailTypes.INBOX.value).count() for u in target_users]
        for v in inbox_mail_count_list:
            for new_v in new_inbox_mail_count_list:
                self.assertEqual(v + 1, new_v)

        # у отправителья должно появиться одно исходящее письмо
        current_sent_mail_count = self.authorized_user.letters_set.filter(type=EmailTypes.SENT.value).count()
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

