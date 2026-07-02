from django.db import migrations


def create_ground_editors_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Ground = apps.get_model("grounds", "Ground")

    group, _ = Group.objects.get_or_create(name="Ground Editors")

    ground_ct = ContentType.objects.get_for_model(Ground)
    perms = Permission.objects.filter(
        content_type=ground_ct,
        codename__in=["view_ground", "change_ground"],
    )
    group.permissions.set(perms)


def remove_ground_editors_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Ground Editors").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("grounds", "0007_add_match_model"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_ground_editors_group, remove_ground_editors_group),
    ]
