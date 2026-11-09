from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

from .models import Called


# class CalledChoiceField(forms.ModelChoiceField):
#     def label_from_instance(self, call):
#         date = call.date_call.strftime('%d.%m.%Y %H:%M') if call.date_call else 'Дата неизвестна'
#         return f'{date} · {call.number_phone or "Номер неизвестен"} · {call.record_call_id}'


class NewsForm(forms.Form):
    text = forms.CharField(
        label='Текст новости',
        max_length=2500,
        strip=True,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
    )


class EmployeeCreateForm(forms.ModelForm):
    username = forms.CharField(
        label='Логин',
        max_length=150,
        required=True,
        error_messages={'required': 'Обязательное поле.'},
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    first_name = forms.CharField(
        label='Имя',
        max_length=150,
        required=True,
        error_messages={'required': 'Обязательное поле.'},
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        label='Фамилия',
        max_length=150,
        required=True,
        error_messages={'required': 'Обязательное поле.'},
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        label='Электронная почта',
        max_length=254,
        required=True,
        error_messages={
            'required': 'Обязательное поле.',
            'invalid': 'Введите корректный адрес электронной почты.',
        },
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email')

    def save(self, commit=True):
        employee = super().save(commit=False)
        employee.set_unusable_password()
        if commit:
            employee.save()
        return employee


class EmployeeUpdateForm(forms.ModelForm):
    username = forms.CharField(
        label='Логин',
        max_length=150,
        required=True,
        error_messages={'required': 'Обязательное поле.'},
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    first_name = forms.CharField(
        label='Имя',
        max_length=150,
        required=True,
        error_messages={'required': 'Обязательное поле.'},
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        label='Фамилия',
        max_length=150,
        required=True,
        error_messages={'required': 'Обязательное поле.'},
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        label='Электронная почта',
        max_length=254,
        required=True,
        error_messages={
            'required': 'Обязательное поле.',
            'invalid': 'Введите корректный адрес электронной почты.',
        },
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email')


# class AudioRatingForm(forms.Form):
#     target_user = forms.ModelChoiceField(
#         queryset=get_user_model().objects.none(),
#         label='Пользователь',
#         empty_label='Выберите пользователя',
#         widget=forms.Select(attrs={'class': 'form-select'}),
#     )
#     audio_file = forms.FileField(
#         label='MP3-файл',
#         validators=[FileExtensionValidator(allowed_extensions=['mp3'])],
#         widget=forms.ClearableFileInput(
#             attrs={'class': 'form-control', 'accept': '.mp3,audio/mpeg'},
#         ),
#     )
#     rating = forms.IntegerField(
#         label='Оценка (от 1 до 50)',
#         min_value=1,
#         max_value=5,
#         widget=forms.NumberInput(
#             attrs={'class': 'form-control', 'min': 1, 'max': 50, 'step': 1},
#         ),
#     )

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['target_user'].queryset = get_user_model().objects.filter(
#             is_superuser=False,
#         ).order_by('username')


# class CallRecordingUploadForm(forms.Form):
#     call = CalledChoiceField(
#         queryset=Called.objects.none(),
#         label='Звонок',
#         empty_label='Выберите звонок',
#         widget=forms.Select(attrs={'class': 'form-select'}),
#     )
#     audio_file = forms.FileField(
#         label='Запись звонка (MP3)',
#         validators=[FileExtensionValidator(allowed_extensions=['mp3'])],
#         widget=forms.ClearableFileInput(
#             attrs={'class': 'form-control', 'accept': '.mp3,audio/mpeg'},
#         ),
#     )

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['call'].queryset = Called.objects.filter(
#             record_call_id__isnull=False,
#         ).exclude(record_call_id='').order_by('-date_call')
