"""
URL configuration for aivonx project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from .views import HealthCheckView
from proxy.handlers import health as proxy_health
from proxy.web import ProxyLoginView, proxy_logout_view, manage as proxy_manage

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health', HealthCheckView.as_view(), name='health-check'),
    path("api/proxy/", include("proxy.urls")),
    path("api/proxy", proxy_health),
    path("api/account/", include("account.urls")),
    # Web UI
    path('', ProxyLoginView.as_view(), name='proxy_ui_login'),
    path('ui/logout', proxy_logout_view, name='proxy_ui_logout'),
    path('ui/manage', proxy_manage, name='proxy_ui_manage'),
]

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns += [
    path('api/schema', SpectacularAPIView.as_view(), name='schema'), # OpenAPI 3 schema YAML
    path('swagger', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

from django.conf import settings
if settings.DEBUG:
    # Serve static files from app 'static/' directories during development
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()