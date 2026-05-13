# Tədris ili üzrə tələbə və qrup ayırması

from django.db import migrations, models


def _bucket_academic_year_start(registration_date):
    if registration_date.month >= 9:
        return registration_date.year
    return registration_date.year - 1


def forwards_bucket_years(apps, schema_editor):
    Student = apps.get_model("students", "Student")
    StudentGroup = apps.get_model("students", "StudentGroup")

    for s in Student.objects.all():
        ay = _bucket_academic_year_start(s.registration_date)
        Student.objects.filter(pk=s.pk).update(academic_year_start=ay)

    fallback_empty_group = 2025
    for g in StudentGroup.objects.all():
        ys = list(
            Student.objects.filter(student_group_id=g.pk)
            .values_list("academic_year_start", flat=True)
            .distinct()
        )
        ys = [y for y in ys if y is not None]
        if len(ys) == 1:
            y = ys[0]
        elif len(ys) > 1:
            y = min(ys)
        else:
            y = fallback_empty_group
        StudentGroup.objects.filter(pk=g.pk).update(academic_year_start=y)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0005_studentgroup_lesson_weekdays"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentgroup",
            name="name",
            field=models.CharField(max_length=80, verbose_name="Qrupun adı"),
        ),
        migrations.AddField(
            model_name="studentgroup",
            name="academic_year_start",
            field=models.PositiveSmallIntegerField(
                null=True,
                verbose_name="Tədris ili (başlanğıc ili)",
                help_text="1 Sentyabr ilə başlayan tədris ili üçün təqvim ili (məs. 2025 → 2025/09–2026/08).",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="academic_year_start",
            field=models.PositiveSmallIntegerField(
                null=True,
                verbose_name="Tədris ili (başlanğıc ili)",
                help_text="Bu tələbə hansı tədris ili üçün qeydiyyatdadır (avtomatik köçürülmür).",
            ),
        ),
        migrations.RunPython(forwards_bucket_years, backwards_noop),
        migrations.AlterField(
            model_name="studentgroup",
            name="academic_year_start",
            field=models.PositiveSmallIntegerField(
                verbose_name="Tədris ili (başlanğıc ili)",
                help_text="1 Sentyabr ilə başlayan tədris ili üçün təqvim ili (məs. 2025 → 2025/09–2026/08).",
            ),
        ),
        migrations.AlterField(
            model_name="student",
            name="academic_year_start",
            field=models.PositiveSmallIntegerField(
                verbose_name="Tədris ili (başlanğıc ili)",
                help_text="Bu tələbə hansı tədris ili üçün qeydiyyatdadır (avtomatik köçürülmür).",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentgroup",
            constraint=models.UniqueConstraint(
                fields=("name", "academic_year_start"),
                name="students_studentgroup_name_academic_year_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(
                fields=["academic_year_start", "is_archived"],
                name="students_st_academi_8a1b2c_idx",
            ),
        ),
    ]
