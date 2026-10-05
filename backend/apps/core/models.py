from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AppSetting(TimeStampedModel):
    """Tunable key-value setting editable by admins (specs/02 §2, specs/07 §6)."""

    class ValueType(models.TextChoices):
        INT = "int", "정수"
        FLOAT = "float", "실수"
        BOOL = "bool", "참/거짓"
        STR = "str", "문자열"
        JSON = "json", "JSON"

    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(null=True, blank=True)
    value_type = models.CharField(max_length=10, choices=ValueType.choices)
    group = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["group", "key"]

    def __str__(self):
        return self.key
