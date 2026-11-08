from tempfile import TemporaryDirectory

from django.db import connection
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import CallRate, Called, CallRecording, News, NewsRate, Task


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
		cls.created_called_table = Called._meta.db_table not in connection.introspection.table_names()
		if cls.created_called_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.create_model(Called)
		cls.created_call_rate_table = CallRate._meta.db_table not in connection.introspection.table_names()
		if cls.created_call_rate_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.create_model(CallRate)
		cls.created_task_table = Task._meta.db_table not in connection.introspection.table_names()
		if cls.created_task_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.create_model(Task)

	@classmethod
	def tearDownClass(cls):
		if cls.created_task_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.delete_model(Task)
		if cls.created_call_rate_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.delete_model(CallRate)
		if cls.created_called_table:
			with connection.schema_editor() as schema_editor:
				schema_editor.delete_model(Called)
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

	def test_do_page_shows_only_current_users_calls(self):
		other_user = User.objects.create_user(username='other-user', password='secure-password')
		own_call = Called.objects.create(
			number_phone='1234567890',
			date_call=timezone.now(),
			user_call=self.user,
		)
		Called.objects.create(
			number_phone='0987654321',
			date_call=timezone.now(),
			user_call=other_user,
		)
		self.client.force_login(self.user)

		response = self.client.get(reverse('do'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, own_call.number_phone)
		self.assertNotContains(response, '0987654321')
		self.assertContains(response, 'Дата звонка')

	def test_do_page_shows_only_current_users_tasks(self):
		other_user = User.objects.create_user(username='other-task-user', password='secure-password')
		own_task = Task.objects.create(
			number_task='TASK-001',
			start_date_task=timezone.now(),
			closed_date_task=timezone.now(),
			closed_user_task=self.user,
		)
		Task.objects.create(
			number_task='TASK-002',
			start_date_task=timezone.now(),
			closed_user_task=other_user,
		)
		self.client.force_login(self.user)

		response = self.client.get(reverse('do'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, own_task.number_task)
		self.assertNotContains(response, 'TASK-002')
		self.assertContains(response, 'Дата открытия')
		self.assertContains(response, 'Дата закрытия')

	def test_rate_page_shows_only_current_users_call_ratings(self):
		own_call = Called.objects.create(number_phone='1234567890', user_call=self.user)
		other_user = User.objects.create_user(username='other-rater', password='secure-password')
		other_call = Called.objects.create(number_phone='0987654321', user_call=other_user)
		CallRate.objects.create(
			id_call=own_call,
			rate=4.5,
			date_rate=timezone.now(),
			rate_text='Отличный разговор',
		)
		CallRate.objects.create(
			id_call=other_call,
			rate=2.0,
			date_rate=timezone.now(),
			rate_text='Чужая оценка',
		)
		self.client.force_login(self.user)

		response = self.client.get(reverse('rate'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Оценка звонков')
		self.assertContains(response, 'Оценки задач')
		self.assertContains(response, 'Отличный разговор')
		self.assertContains(response, '1234567890')
		self.assertNotContains(response, 'Чужая оценка')
		self.assertNotContains(response, '0987654321')
		self.assertNotContains(response, 'Рейтинг новостей')


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

	def test_superuser_can_deactivate_news(self):
		news_item = News.objects.create(
			text='Новость для удаления',
			create_date=timezone.now(),
			author=self.supervisor,
		)
		self.client.force_login(self.supervisor)

		response = self.client.post(reverse('deactivate_news', args=[news_item.pk]))

		self.assertRedirects(response, reverse('news'))
		news_item.refresh_from_db()
		self.assertFalse(news_item.is_active)
		self.assertNotContains(self.client.get(reverse('news')), 'Новость для удаления')

	def test_regular_user_cannot_deactivate_news(self):
		news_item = News.objects.create(
			text='Новость для удаления',
			create_date=timezone.now(),
			author=self.supervisor,
		)
		self.client.force_login(self.regular_user)

		response = self.client.post(reverse('deactivate_news', args=[news_item.pk]))

		self.assertEqual(response.status_code, 403)
		news_item.refresh_from_db()
		self.assertTrue(news_item.is_active)

	def test_inactive_news_is_hidden_and_delete_button_is_admin_only(self):
		News.objects.create(text='Активная новость', is_active=True)
		News.objects.create(text='Неактивная новость', is_active=False)
		self.client.force_login(self.regular_user)

		response = self.client.get(reverse('news'))

		self.assertContains(response, 'Активная новость')
		self.assertNotContains(response, 'Неактивная новость')
		self.assertNotContains(response, 'Удалить новость')

		self.client.force_login(self.supervisor)
		response = self.client.get(reverse('news'))
		self.assertContains(response, 'Удалить новость')

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
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AudioRating


class AudioRatingPageTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password',
        )
        self.user = user_model.objects.create_user(
            username='employee',
            password='password',
        )

    def test_only_superusers_can_open_page(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('record')).status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.get(reverse('record'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'employee')
        self.assertNotContains(response, 'admin')

    def test_upload_and_rating_are_saved_for_selected_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('record'),
            {
                'target_user': self.user.pk,
                'rating': 4,
                'audio_file': SimpleUploadedFile(
                    'sample.mp3',
                    b'ID3 audio sample',
                    content_type='audio/mpeg',
                ),
            },
        )

        self.assertRedirects(response, reverse('record'))
        saved_rating = AudioRating.objects.get()
        self.assertEqual(saved_rating.user, self.user)
        self.assertEqual(saved_rating.rating, 4)
        self.assertTrue(saved_rating.audio_file.name.endswith('.mp3'))

    def test_superuser_cannot_be_selected_as_rating_recipient(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('record'),
            {
                'target_user': self.admin.pk,
                'rating': 4,
                'audio_file': SimpleUploadedFile('sample.mp3', b'ID3 audio sample'),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AudioRating.objects.exists())

    def test_non_mp3_file_is_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('record'),
            {
                'target_user': self.user.pk,
                'rating': 4,
                'audio_file': SimpleUploadedFile('sample.wav', b'audio sample'),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AudioRating.objects.exists())


class CallRecordingTests(UnmanagedNewsTablesMixin, TransactionTestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        self.user = User.objects.create_user(username='employee', password='password')
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password',
        )
        self.call = Called.objects.create(
            number_phone='1234567890',
            date_call=timezone.now(),
            record_call_id='0a8d05fb-d7c5-11f1-b997-5c60ba5f55bd',
            user_call=self.user,
        )
        CallRate.objects.create(
            id_call=self.call,
            rate=4.5,
            date_rate=timezone.now(),
            rate_text='Хороший звонок',
        )

    def test_owner_can_play_recorded_rated_call(self):
        CallRecording.objects.create(
            record_call_id=self.call.record_call_id,
            audio_file=SimpleUploadedFile('call.mp3', b'ID3 call audio'),
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('play_call_recording', args=[self.call.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'audio/mpeg')
        self.assertEqual(b''.join(response.streaming_content), b'ID3 call audio')

    def test_other_user_cannot_play_call_recording(self):
        CallRecording.objects.create(
            record_call_id=self.call.record_call_id,
            audio_file=SimpleUploadedFile('call.mp3', b'ID3 call audio'),
        )
        other_user = User.objects.create_user(username='other', password='password')
        self.client.force_login(other_user)

        response = self.client.get(
            reverse('play_call_recording', args=[self.call.pk]),
        )

        self.assertEqual(response.status_code, 404)

    def test_call_rating_page_includes_playback_for_available_recording(self):
        CallRecording.objects.create(
            record_call_id=self.call.record_call_id,
            audio_file=SimpleUploadedFile('call.mp3', b'ID3 call audio'),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('rate'))

        self.assertContains(response, 'Хороший звонок')
        self.assertContains(response, '<audio', html=False)
        self.assertContains(
            response,
            reverse('play_call_recording', args=[self.call.pk]),
        )

    def test_superuser_can_upload_recording_for_call(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('upload_call_recording'),
            {
                'call': self.call.pk,
                'audio_file': SimpleUploadedFile('call.mp3', b'ID3 call audio'),
            },
        )

        self.assertRedirects(response, reverse('upload_call_recording'))
        recording = CallRecording.objects.get()
        self.assertEqual(recording.record_call_id, self.call.record_call_id)
        self.assertTrue(recording.audio_file.name.endswith('.mp3'))

    def test_regular_user_cannot_upload_recordings(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('upload_call_recording'))

        self.assertEqual(response.status_code, 403)
