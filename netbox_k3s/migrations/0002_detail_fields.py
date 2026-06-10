from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_k3s", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="k3scluster",
            name="node_count",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="k3spod",
            name="restarts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="k3spod",
            name="container_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="k3spod",
            name="started",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="k3spod",
            name="labels",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="k3sservice",
            name="external_ip",
            field=models.CharField(blank=True, max_length=253),
        ),
        migrations.AddField(
            model_name="k3sservice",
            name="selector",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
