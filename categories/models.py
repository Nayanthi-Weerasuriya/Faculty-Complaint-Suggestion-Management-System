from django.db import models


class Category(models.Model):
    """
    Complaint / Suggestion Categories (e.g. Classroom, IT, Maintenance, Examination, Other)
    Can be dynamically configured by administrators without code changes (Section 12 Non-functional reqs).
    """
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name
