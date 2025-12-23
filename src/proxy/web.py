from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages

from .models import node, ProxyConfig
from .forms import NodeForm, ProxyConfigForm


class ProxyLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('proxy_ui_manage')


class ProxyLogoutView(LogoutView):
    next_page = reverse_lazy('proxy_ui_login')


def proxy_logout_view(request):
    """Log out user and redirect to proxy UI login page.

    Using an explicit function ensures we always redirect to the
    intended login URL.
    """
    from django.contrib.auth import logout
    from django.shortcuts import redirect
    logout(request)
    try:
        from django.urls import reverse
        return redirect(reverse('proxy_ui_login'))
    except Exception:
        return redirect('')


@csrf_protect
@login_required
def manage(request):
    # Ensure config exists
    cfg = ProxyConfig.objects.order_by('-updated_at').first()
    if cfg is None:
        cfg = ProxyConfig.objects.create()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_node':
            form = NodeForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Node added')
                return redirect(reverse('proxy_ui_manage'))
            else:
                messages.error(request, 'Invalid node data')
        elif action == 'edit_node':
            node_id = request.POST.get('node_id')
            nd = get_object_or_404(node, pk=node_id)
            form = NodeForm(request.POST, instance=nd)
            if form.is_valid():
                form.save()
                messages.success(request, 'Node updated')
                return redirect(reverse('proxy_ui_manage'))
            else:
                messages.error(request, 'Invalid node data')
        elif action == 'delete_node':
            node_id = request.POST.get('node_id')
            nd = get_object_or_404(node, pk=node_id)
            nd.delete()
            messages.success(request, 'Node deleted')
            return redirect(reverse('proxy_ui_manage'))
        elif action == 'update_config':
            form = ProxyConfigForm(request.POST, instance=cfg)
            if form.is_valid():
                form.save()
                messages.success(request, 'Config updated')
                return redirect(reverse('proxy_ui_manage'))
            else:
                messages.error(request, 'Invalid config')

    nodes = node.objects.all().order_by('id')
    node_form = NodeForm()
    config_form = ProxyConfigForm(instance=cfg)

    return render(request, 'manage.html', {
        'nodes': nodes,
        'node_form': node_form,
        'config_form': config_form,
        'config': cfg,
    })
