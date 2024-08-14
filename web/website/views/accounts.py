"""
Views for manipulating Accounts.

"""
from evennia.web.website.views.accounts import AccountCreateView as DefaultAccountCreateView
#from web.website.forms import AccountForm
#from characters.skills import _SKILL_TREE


class AccountCreateView(DefaultAccountCreateView):
#	form_class = AccountForm

	def get_form(self, form_class=None):
		form = super().get_form(form_class=form_class)
		form.fields['password2'].help_text = None
		form.fields['password2'].label = ""
		form.fields['password2'].required = True
		form.fields['email'].help_text = None
		return form
