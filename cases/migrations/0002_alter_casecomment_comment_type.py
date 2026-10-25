# Generated manually to record the reporter reply choice; no database column changes are required.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cases', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='casecomment',
            name='comment_type',
            field=models.CharField(
                choices=[
                    ('internal', 'Internal Authority Note'),
                    ('progress', 'Progress Update'),
                    ('info_request', 'Information Request'),
                    ('reporter_reply', 'Reporter Reply / Clarification'),
                ],
                default='progress',
                max_length=20,
            ),
        ),
    ]
