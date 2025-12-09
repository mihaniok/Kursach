from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Group, Subject
from django.core.exceptions import ValidationError
from django.conf import settings

class RegistrationForm(UserCreationForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label='Группа'
    )
    
    class Meta:
        model = User
        fields = (
            'email',
            'last_name',
            'first_name',
            'middle_name',
            'phone_number',
            'group',
            'password1',
            'password2',
        )
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class TeacherRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            'email',
            'last_name',
            'first_name',
            'middle_name',
            'phone_number',
            'password1',
            'password2',
        )
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        if commit:
            user.save()
        return user

class TeacherSubjectsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = []
    
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Предметы'
    )
      
class ProfileForm(forms.ModelForm):
    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > settings.MAX_UPLOAD_SIZE:
                raise ValidationError("Файл слишком большой. Максимальный размер - 2MB.")
            return avatar
        return None
    
    class Meta:
        model = User
        fields = [
            'last_name', 
            'first_name', 
            'middle_name',
            'email',
            'phone_number',
            'avatar'
        ]
        widgets = {
            'course': forms.Select(choices=[(i, f"{i} курс") for i in range(1, 7)]),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }
        
class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autofocus': True})
    )
    
    error_messages = {
        'invalid_login': "Пожалуйста, введите правильный email и пароль.",
        'inactive': "Этот аккаунт неактивен.",
    }