from django import forms


class NewsForm(forms.Form):
    text = forms.CharField(
        label='Текст новости',
        max_length=2500,
        strip=True,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
    )
