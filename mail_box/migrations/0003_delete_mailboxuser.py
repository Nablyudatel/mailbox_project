# Generated by Django 2.2.5 on 2019-12-20 10:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mail_box', '0002_auto_20191220_1226'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MailboxUser',
        ),
    ]