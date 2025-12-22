from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect


@csrf_protect
@login_required
def logs_page(request):
    """Render a single read-only logs page.
    """
    return render(request, 'logviewer/logviewer.html', {})
