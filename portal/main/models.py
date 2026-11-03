from django.conf import settings
from django.db import models


class News(models.Model):
    id = models.AutoField(primary_key=True)
    text = models.CharField(max_length=2500, blank=True, null=True)
    create_date = models.DateTimeField(db_column='createDate', blank=True, null=True)
    is_active = models.BooleanField(db_column='isActive', blank=True, null=True, default=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column='author',
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'news'
        managed = False
        ordering = ('-create_date',)

    def __str__(self):
        return self.text or f'Новость {self.pk}'


class NewsRate(models.Model):
    id = models.AutoField(primary_key=True)
    like_news = models.BooleanField(blank=True, null=True)
    dislike_news = models.BooleanField(blank=True, null=True)
    author_rate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column='author_rate',
        related_name='news_rates',
        blank=True,
        null=True,
    )
    date_rate = models.DateTimeField(blank=True, null=True)
    news = models.ForeignKey(
        News,
        on_delete=models.DO_NOTHING,
        db_column='news_id',
        related_name='rates',
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'news_rate'
        managed = False


class Called(models.Model):
    id = models.AutoField(primary_key=True)
    number_phone = models.CharField(max_length=10, blank=True, null=True)
    date_call = models.DateTimeField(blank=True, null=True)
    record_call_id = models.CharField(max_length=36, blank=True, null=True)
    user_call = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column='user_call',
        related_name='calls',
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'called'
        managed = False
        ordering = ('-date_call',)


class Task(models.Model):
    id = models.AutoField(primary_key=True)
    number_task = models.CharField(max_length=10, blank=True, null=True)
    start_date_task = models.DateTimeField(blank=True, null=True)
    closed_date_task = models.DateTimeField(blank=True, null=True)
    closed_user_task = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_column='closed_user_task',
        related_name='closed_tasks',
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'task'
        managed = False
        ordering = ('-start_date_task',)
