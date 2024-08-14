from django.http import Http404

def not_found(request):
		raise Http404
