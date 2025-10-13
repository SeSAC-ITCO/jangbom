from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    nickname = forms.CharField(max_length=30)

    class Meta:
        model = CustomUser
        fields = ('username', 'nickname', 'password1', 'password2')


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(label="아이디")
    password = forms.CharField(label="비밀번호", widget=forms.PasswordInput)
