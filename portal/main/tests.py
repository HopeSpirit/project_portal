from django.db import connection
from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import News, NewsRate


class UnmanagedNewsTablesMixin:
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		existing_tables = connection.introspection.table_names()
		cls.created_news_table = News._meta.db_table not in existing_tables
		if cls.created_news_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.create_model(News)
		cls.created_rate_table = NewsRate._meta.db_table not in connection.introspection.table_names()
		if cls.created_rate_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.create_model(NewsRate)

	@classmethod
	def tearDownClass(cls):
		if cls.created_rate_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.delete_model(NewsRate)
		if cls.created_news_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.delete_model(News)
		super().tearDownClass()


class LoginTests(UnmanagedNewsTablesMixin, TransactionTestCase):
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


class NewsPublishingTests(UnmanagedNewsTablesMixin, TransactionTestCase):
	def setUp(self):
		NewsRate.objects.all().delete()
		News.objects.all().delete()
		self.supervisor = User.objects.create_superuser(
			username='supervisor',
			password='secure-password',
			email='supervisor@example.com',
		)
		self.regular_user = User.objects.create_user(username='reader', password='secure-password')

	def test_supervisor_can_publish_news(self):
		self.client.force_login(self.supervisor)

		response = self.client.post(reverse('add_news'), {'text': 'Обновление компании'})

		self.assertRedirects(response, reverse('news'))
		news_item = News.objects.get()
		self.assertEqual(news_item.text, 'Обновление компании')
		self.assertEqual(news_item.author, self.supervisor)
		self.assertIsNotNone(news_item.create_date)

	def test_regular_user_sees_news_but_cannot_publish(self):
		News.objects.create(
			text='Опубликованная новость',
			create_date=timezone.now(),
			author=self.supervisor,
		)
		self.client.force_login(self.regular_user)

		response = self.client.get(reverse('news'))

		self.assertContains(response, 'Опубликованная новость')
		self.assertNotContains(response, 'Добавить новость')

		response = self.client.post(reverse('add_news'), {'text': 'Неавторизованная публикация'})

		self.assertEqual(response.status_code, 403)
		self.assertEqual(News.objects.count(), 1)

	def test_supervisor_sees_news_form(self):
		self.client.force_login(self.supervisor)

		response = self.client.get(reverse('news'))

		self.assertContains(response, 'Добавить новость')

	def test_regular_user_can_like_and_change_vote(self):
		news_item = News.objects.create(text='Новость для голосования', create_date=timezone.now())
		self.client.force_login(self.regular_user)

		response = self.client.post(reverse('rate_news', args=[news_item.pk]), {'vote': 'like'})
		self.assertRedirects(response, reverse('news'))
		rate = NewsRate.objects.get(news=news_item, author_rate=self.regular_user)
		self.assertTrue(rate.like_news)
		self.assertFalse(rate.dislike_news)
		self.assertIsNotNone(rate.date_rate)

		self.client.post(reverse('rate_news', args=[news_item.pk]), {'vote': 'dislike'})
		rate.refresh_from_db()
		self.assertFalse(rate.like_news)
		self.assertTrue(rate.dislike_news)
		self.assertEqual(
			NewsRate.objects.filter(news=news_item, author_rate=self.regular_user).count(),
			1,
		)

	def test_ajax_vote_returns_counts_without_redirect(self):
		news_item = News.objects.create(text='Новость для голосования', create_date=timezone.now())
		self.client.force_login(self.regular_user)

		response = self.client.post(
			reverse('rate_news', args=[news_item.pk]),
			{'vote': 'like'},
			HTTP_X_REQUESTED_WITH='XMLHttpRequest',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {
			'like_count': 1,
			'dislike_count': 0,
			'user_vote': 'like',
		})

	def test_superuser_cannot_vote(self):
		news_item = News.objects.create(text='Новость для голосования', create_date=timezone.now())
		self.client.force_login(self.supervisor)

		response = self.client.post(reverse('rate_news', args=[news_item.pk]), {'vote': 'like'})

		self.assertEqual(response.status_code, 403)
		self.assertFalse(NewsRate.objects.filter(news=news_item).exists())

	def test_invalid_vote_is_rejected(self):
		news_item = News.objects.create(text='Новость для голосования', create_date=timezone.now())
		self.client.force_login(self.regular_user)

		response = self.client.post(reverse('rate_news', args=[news_item.pk]), {'vote': 'other'})

		self.assertEqual(response.status_code, 400)
		self.assertFalse(NewsRate.objects.filter(news=news_item).exists())

	def test_vote_counts_are_shown_to_regular_users(self):
		news_item = News.objects.create(text='Популярная новость', create_date=timezone.now())
		NewsRate.objects.create(
			like_news=True,
			dislike_news=False,
			author_rate=self.supervisor,
			date_rate=timezone.now(),
			news=news_item,
		)
		self.client.force_login(self.regular_user)

		response = self.client.get(reverse('news'))

		rendered_news = response.context['news_list'][0]
		self.assertEqual(rendered_news.like_count, 1)
		self.assertEqual(rendered_news.dislike_count, 0)
