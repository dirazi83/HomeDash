from django import forms
from .models import Service

class ServiceForm(forms.ModelForm):
    # Dummy field to accept plain text API key to encrypt
    api_key_input = forms.CharField(
        required=False, 
        widget=forms.PasswordInput(attrs={'placeholder': 'Paste API Key or Token', 'class': 'w-full bg-slate-800 border-slate-700 rounded-lg text-slate-200 focus:ring-accent focus:border-accent'})
    )
    password_input = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password (if required)', 'class': 'w-full bg-slate-800 border-slate-700 rounded-lg text-slate-200 focus:ring-accent focus:border-accent'})
    )

    class Meta:
        model = Service
        fields = ['name', 'service_type', 'url', 'username', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-slate-800 border-slate-700 rounded-lg text-slate-200 focus:ring-accent focus:border-accent'}),
            'service_type': forms.Select(attrs={'class': 'w-full bg-slate-800 border-slate-700 rounded-lg text-slate-200 focus:ring-accent focus:border-accent'}),
            'url': forms.URLInput(attrs={'placeholder': 'http://192.168.1.50:8989', 'class': 'w-full bg-slate-800 border-slate-700 rounded-lg text-slate-200 focus:ring-accent focus:border-accent'}),
            'username': forms.TextInput(attrs={'class': 'w-full bg-slate-800 border-slate-700 rounded-lg text-slate-200 focus:ring-accent focus:border-accent'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-accent bg-slate-800 border-slate-700 rounded focus:ring-accent focus:ring-2'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Update encrypted fields if new ones are provided
        if self.cleaned_data.get('api_key_input'):
            instance.api_key = self.cleaned_data['api_key_input']
        if self.cleaned_data.get('password_input'):
            instance.password = self.cleaned_data['password_input']
        if commit:
            instance.save()
        return instance
