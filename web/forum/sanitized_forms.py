from django import forms
from django.conf import settings
import bleach

# base
ALLOWED_TAGS = getattr(settings, "BLEACH_ALLOWED_TAGS", bleach.sanitizer.ALLOWED_TAGS)
ALLOWED_ATTRIBUTES = getattr(settings, "BLEACH_ALLOWED_ATTRIBUTES", bleach.sanitizer.ALLOWED_ATTRIBUTES)
ALLOWED_PROTOCOLS = getattr(settings, "BLEACH_ALLOWED_PROTOCOLS", bleach.sanitizer.ALLOWED_PROTOCOLS)
STRIP_TAGS = getattr(settings, "BLEACH_STRIP_TAGS", False)
STRIP_COMMENTS = getattr(settings, "BLEACH_STRIP_COMMENTS", False)

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
            print(self.bleach_kwargs)
            data = bleach.clean(data, **self.bleach_kwargs)
        if not data and self.required:
            raise forms.ValidationError(self.get_error_message())
        return data