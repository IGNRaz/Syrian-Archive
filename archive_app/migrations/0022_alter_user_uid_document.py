# Generated migration to change uid_document from ImageField to FileField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive_app', '0021_user_intended_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='uid_document',
            field=models.FileField(blank=True, null=True, upload_to='uid_docs/'),
        ),
    ]