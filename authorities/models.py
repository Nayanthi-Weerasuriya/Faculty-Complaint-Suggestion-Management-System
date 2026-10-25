from django.db import models


class Authority(models.Model):
    """
    Represents an action-taking authority entity within the faculty
    (e.g., Maintenance Division, IT Unit, Examination Unit, Dean's Office).
    Matches Appendix A: Preliminary Data Entities.
    """
    name = models.CharField(max_length=150, unique=True, help_text="Name of the department or authority unit")
    officer_name = models.CharField(max_length=150, help_text="Name of the officer-in-charge")
    designation = models.CharField(max_length=150, help_text="Official designation of the officer")
    email = models.EmailField(help_text="Official contact email")
    phone = models.CharField(max_length=25, blank=True, help_text="Contact telephone / extension")
    unit = models.CharField(max_length=150, blank=True, help_text="Sub-unit or faculty division")
    is_active = models.BooleanField(default=True, help_text="Active status in the faculty authority list")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Authority"
        verbose_name_plural = "Authorities"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.officer_name})"
