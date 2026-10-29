from django import forms
from .models import CaseStatus, CasePriority
from categories.models import Category
from authorities.models import Authority


class DateRangeFilterForm(forms.Form):
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('date_from') and data.get('date_to') and data['date_from'] > data['date_to']:
            raise forms.ValidationError('The start date must be before the end date.')
        return data


class ReportFilterForm(DateRangeFilterForm):
    category = forms.ModelChoiceField(required=False, queryset=Category.objects.all())
    authority = forms.ModelChoiceField(required=False, queryset=Authority.objects.all())
    priority = forms.ChoiceField(required=False, choices=[('', 'All priorities')] + list(CasePriority.choices))
    status = forms.ChoiceField(required=False, choices=[('', 'All statuses')] + list(CaseStatus.choices))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def apply(self, cases):
        if not self.is_valid():
            return cases.none()
        for field in ['category', 'authority', 'priority', 'status']:
            if self.cleaned_data.get(field):
                cases = cases.filter(**{'assigned_authority' if field == 'authority' else field: self.cleaned_data[field]})
        if self.cleaned_data.get('date_from'):
            cases = cases.filter(submitted_at__date__gte=self.cleaned_data['date_from'])
        if self.cleaned_data.get('date_to'):
            cases = cases.filter(submitted_at__date__lte=self.cleaned_data['date_to'])
        return cases
