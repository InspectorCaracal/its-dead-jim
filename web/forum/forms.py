import bleach
from django import forms
from django.conf import settings
from tinymce.widgets import TinyMCE

from .models import (Poll, Topic, Post)

# base
ALLOWED_TAGS = getattr(settings, "BLEACH_ALLOWED_TAGS", bleach.sanitizer.ALLOWED_TAGS)
ALLOWED_ATTRIBUTES = getattr(settings, "BLEACH_ALLOWED_ATTRIBUTES", bleach.sanitizer.ALLOWED_ATTRIBUTES)
ALLOWED_PROTOCOLS = getattr(settings, "BLEACH_ALLOWED_PROTOCOLS", bleach.sanitizer.ALLOWED_PROTOCOLS)
STRIP_TAGS = getattr(settings, "BLEACH_STRIP_TAGS", False)
STRIP_COMMENTS = getattr(settings, "BLEACH_STRIP_COMMENTS", True)

CSS_SANITIZER = None
# CSS - optional dependency
if hasattr(bleach, 'css_sanitizer'):
    ALLOWED_CSS_PROPERTIES = getattr(settings, 'BLEACH_ALLOWED_CSS_PROPERTIES', bleach.css_sanitizer.ALLOWED_CSS_PROPERTIES)
    ALLOWED_SVG_PROPERTIES = getattr(settings, 'BLEACH_ALLOWED_SVG_PROPERTIES', bleach.css_sanitizer.ALLOWED_SVG_PROPERTIES)
    CSS_SANITIZER = bleach.css_sanitizer.CSSSanitizer(
        allowed_css_properties=ALLOWED_CSS_PROPERTIES,
        allowed_svg_properties=ALLOWED_SVG_PROPERTIES,
    )


class BleachedCharField(forms.CharField):
    """
    A form CharField that applies bleach to its contents.
    
    Keyword args to pass on to bleach:
        bleach_tags
        bleach_attributes
        bleach_protocols
        bleach_strip
        bleach_strip_comments
        css_sanitizer
    
    See bleach documentation for how to use.
    """
    def __init__(self, *args, **kwargs):
        self.bleach_kwargs = {
            'tags': kwargs.get('bleach_tags', ALLOWED_TAGS),
            'attributes': kwargs.get('bleach_attributes', ALLOWED_ATTRIBUTES),
            'protocols': kwargs.get('bleach_protocols', ALLOWED_PROTOCOLS),
            'strip': kwargs.get('bleach_strip', STRIP_TAGS),
            'strip_comments': kwargs.get('bleach_strip_comments', STRIP_COMMENTS),
            'css_sanitizer': kwargs.get('css_sanitizer', CSS_SANITIZER),
        }
        super().__init__(*args, **kwargs)

    def clean(self, value):
        data = super().clean(value)
        if data:
            data = bleach.clean(data, **self.bleach_kwargs)
        if not data and self.required:
            raise forms.ValidationError(self.get_error_message())
        return data


class NewTopicForm(forms.ModelForm):
    subject = forms.CharField(
        max_length=250,
        widget=forms.TextInput(
            attrs={
                'class': 'form_input',
                'placeholder': '(Topic Subject)',
                'label': 'Subject:'
            }
        )
    )

    content = BleachedCharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))


    class Meta:
        model = Topic
        fields = ['subject', 'content']


class PostForm(forms.ModelForm):

    subject = forms.CharField(
        max_length=250,
        widget=forms.TextInput(
            attrs={
                'class': 'form_input',
                'placeholder': '',
                'label': 'Subject:',
            }
        ),
        required=False,
    )

#    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))
    content = BleachedCharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))

    class Meta:
        model = Post
        fields = ['subject', 'content']

class PollForm(forms.Form):
    def __init__(self, *args, **kwargs):
        poll = kwargs.pop('poll', None)
        super().__init__(*args, **kwargs)
        if poll:
            self.fields['options'].choices = list(poll.get_option_choices())
        self.fields['options'].widget.template_name = 'forum_poll_choice.html'

class SingleChoicePoll(PollForm):
    options = forms.ChoiceField(widget=forms.RadioSelect(attrs={'class': 'poll-item'}))


class MultiChoicePoll(PollForm):
    options = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(attrs={'class': 'poll-item'}))
