from django import forms

from .models import Application, Participant


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            'contact_name',
            'gender',
            'birth_date',
            'contact_phone',
            'contact_address',
            'email',
            'postal_code',
            'emergency_contact_name',
            'emergency_contact_relation',
            'emergency_contact_address',
            'emergency_contact_phone',
            'adult_count',
            'child_count',
            'deposit_paid',
            'balance_due_date',
        ]
        widgets = {
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_address': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_address': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'adult_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'child_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'deposit_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'balance_due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['full_name', 'id_card', 'is_contact']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'id_card': forms.TextInput(attrs={'class': 'form-control'}),
            'is_contact': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }