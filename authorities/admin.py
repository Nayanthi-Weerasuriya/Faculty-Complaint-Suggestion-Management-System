from django.contrib import admin
from .models import Authority


@admin.register(Authority)
class AuthorityAdmin(admin.ModelAdmin):
    list_display = ('name', 'officer_name', 'designation', 'email', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'officer_name', 'email', 'unit')
