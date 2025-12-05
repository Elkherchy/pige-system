# Generated migration for MongoDB fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='recording',
            name='mongo_file_id',
            field=models.CharField(blank=True, help_text='ID du fichier dans MongoDB GridFS', max_length=255, null=True, verbose_name='ID fichier MongoDB'),
        ),
        migrations.AddField(
            model_name='recording',
            name='mongo_url',
            field=models.CharField(blank=True, help_text='URL pour télécharger depuis MongoDB', max_length=1024, null=True, verbose_name='URL MongoDB'),
        ),
        migrations.AddField(
            model_name='recording',
            name='local_url',
            field=models.CharField(blank=True, help_text='URL pour télécharger depuis le stockage local', max_length=1024, null=True, verbose_name='URL locale'),
        ),
    ]

