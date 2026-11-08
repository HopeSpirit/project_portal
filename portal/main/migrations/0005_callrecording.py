from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_audiorating'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallRecording',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('record_call_id', models.CharField(max_length=36, unique=True)),
                ('audio_file', models.FileField(upload_to='call_recordings/%Y/%m/%d/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
    ]
