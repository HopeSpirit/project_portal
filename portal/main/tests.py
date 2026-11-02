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
