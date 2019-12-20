from django import forms

from accounts.models import MailboxUser


class EmailForm(forms.Form):
    addressee = forms.ModelMultipleChoiceField(queryset=MailboxUser.objects.all())
    header = forms.CharField(max_length=300)
    text = forms.CharField(max_length=2000, widget=forms.Textarea)


class EmailFormReadonly(forms.Form):
    sender = forms.ModelChoiceField(queryset=MailboxUser.objects.all(), disabled=True)
    addressee = forms.ModelMultipleChoiceField(queryset=MailboxUser.objects.all(), disabled=True)
    header = forms.CharField(max_length=300, disabled=True)
    text = forms.CharField(max_length=2000, widget=forms.Textarea, disabled=True)

