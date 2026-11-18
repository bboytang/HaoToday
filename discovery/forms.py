from django import forms

from .models import Subscription


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ("category", "keyword", "platform", "region", "leads")

    def clean(self):
        data = super().clean()
        if not any(data.get(k) for k in ("category", "keyword", "platform", "region")):
            raise forms.ValidationError("请至少填写一个兴趣条件。")
        return data
