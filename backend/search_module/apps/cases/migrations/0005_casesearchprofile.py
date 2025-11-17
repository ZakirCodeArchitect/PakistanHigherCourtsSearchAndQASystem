from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0004_widen_term_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="CaseSearchProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "clean_case_title",
                    models.CharField(blank=True, default="", max_length=800),
                ),
                (
                    "normalized_case_title",
                    models.CharField(blank=True, default="", max_length=800),
                ),
                ("party_tokens", models.JSONField(blank=True, default=list)),
                ("subject_tags", models.JSONField(blank=True, default=list)),
                ("keyword_highlights", models.JSONField(blank=True, default=list)),
                ("summary_text", models.TextField(blank=True, default="")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "case",
                    models.OneToOneField(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="search_profile",
                        to="cases.case",
                    ),
                ),
            ],
            options={
                "db_table": "case_search_profiles",
            },
        ),
        migrations.AddIndex(
            model_name="casesearchprofile",
            index=models.Index(
                fields=["clean_case_title"],
                name="case_search_clean_title_idx",
            ),
        ),
    ]

