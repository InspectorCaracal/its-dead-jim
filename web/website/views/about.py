"""
The main index page, including the game stats

"""

from django.views.generic import TemplateView

class AboutPageView(TemplateView):
    # Tell the view what HTML template to use for the page
    template_name = "website/about.html"
