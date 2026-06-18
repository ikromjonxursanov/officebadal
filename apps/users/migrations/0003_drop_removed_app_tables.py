from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_options'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                'DROP TABLE IF EXISTS duties_dutyassignment;',
                'DROP TABLE IF EXISTS duties_dutycycle;',
                'DROP TABLE IF EXISTS expenses_expense;',
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
