from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse


class LoginTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='test-user', password='secure-password')

	def test_valid_credentials_log_user_in(self):
		response = self.client.post(
			reverse('index'),
			{'username': 'test-user', 'password': 'secure-password'},
			follow=True,
		)

		self.assertTrue(response.wsgi_request.user.is_authenticated)
		self.assertContains(response, 'Вы успешно вошли в систему.')

	def test_invalid_credentials_show_error(self):
		response = self.client.post(
			reverse('index'),
			{'username': 'test-user', 'password': 'wrong-password'},
			follow=True,
		)

		self.assertFalse(response.wsgi_request.user.is_authenticated)
		self.assertContains(response, 'Неверный логин или пароль.')

	def test_authenticated_user_is_redirected_from_login_page(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse('index'))

		self.assertRedirects(response, reverse('main_page'))

	def test_login_redirects_to_requested_internal_page(self):
		response = self.client.post(
			reverse('index'),
			{
				'username': 'test-user',
				'password': 'secure-password',
				'next': reverse('main_page'),
			},
		)

		self.assertRedirects(response, reverse('main_page'))

	def test_login_ignores_external_next_url(self):
		response = self.client.post(
			reverse('index'),
			{
				'username': 'test-user',
				'password': 'secure-password',
				'next': 'https://example.com/',
			},
		)

		self.assertRedirects(response, reverse('main_page'))

	def test_main_page_requires_authentication(self):
		response = self.client.get(reverse('main_page'))

		self.assertRedirects(response, f"{reverse('index')}?next={reverse('main_page')}")

	def test_logout_ends_session(self):
		self.client.force_login(self.user)

		response = self.client.post(reverse('logout'), follow=True)

		self.assertRedirects(response, reverse('index'))
		self.assertFalse(response.wsgi_request.user.is_authenticated)
		self.assertContains(response, 'Вы вышли из системы.')

	def test_logout_rejects_get_requests(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse('logout'))

		self.assertEqual(response.status_code, 405)

	def test_news_page_requires_authentication(self):
		response = self.client.get(reverse('news'))

		self.assertRedirects(response, f"{reverse('index')}?next={reverse('news')}")

	def test_news_page_renders_for_authenticated_user(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse('news'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Новости компании')
