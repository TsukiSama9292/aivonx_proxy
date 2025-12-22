"""
ASGI config for aivonx project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aivonx.settings')

# Get the standard Django ASGI application
django_app = get_asgi_application()


async def application(scope, receive, send):
	"""Custom ASGI application wrapper to handle lifespan events for HA manager initialization."""
	if scope['type'] == 'lifespan':
		# Handle lifespan events to initialize HA manager after Django is fully ready
		while True:
			message = await receive()
			if message['type'] == 'lifespan.startup':
				try:
					# Import here so Django is fully loaded
					from proxy.utils.proxy_manager import HAProxyManager
					import logging
					logger = logging.getLogger('proxy')

					logger.info("ASGI startup: initializing proxy manager...")
					# Create manager and explicitly load nodes from DB in async context
					mgr = HAProxyManager(nodes=None, health_path="/api/health")
					
					# Load nodes from DB using async version to avoid blocking
					try:
						logger.info("ASGI startup: loading nodes from database...")
						await mgr._refresh_from_db_async()
						logger.info("ASGI startup: nodes loaded: %s", mgr.nodes)
					except Exception as e:
						logger.error("ASGI startup: failed to load nodes from DB: %s", e, exc_info=True)
					
					# Run initial model refresh to populate available_models cache
					try:
						logger.info("ASGI startup: refreshing models...")
						await mgr.refresh_models_all()
						logger.info("ASGI startup: models refresh complete")
					except Exception as e:
						logger.error("ASGI startup: models refresh failed: %s", e, exc_info=True)
					
					# Run initial health check to populate latencies and active/standby pools
					try:
						logger.info("ASGI startup: running health checks...")
						await mgr.health_check_all()
						logger.info("ASGI startup: health checks complete")
					except Exception as e:
						logger.error("ASGI startup: health check failed: %s", e, exc_info=True)
					
					# Start the background scheduler for periodic health checks and model refreshes
					try:
						mgr.start_scheduler(interval_minutes=10)
						logger.info("ASGI startup: scheduler started")
					except Exception as e:
						logger.error("ASGI startup: scheduler start failed: %s", e, exc_info=True)
					
					# Set as global manager
					from proxy.utils import proxy_manager as pm_module
					pm_module._global_manager = mgr
					try:
						from django.apps import apps as _django_apps
						_django_apps.get_app_config("proxy").proxy_manager = mgr
						logger.info("ASGI startup: proxy manager attached to AppConfig")
					except Exception:
						logger.warning("ASGI startup: failed to attach manager to AppConfig")
						
					logger.info("ASGI startup: proxy manager initialization complete")
				except Exception as e:
					# Log but don't fail - manager can be initialized on first request
					import logging
					logging.getLogger('proxy').error("ASGI startup: manager initialization failed: %s", e, exc_info=True)
				
				await send({'type': 'lifespan.startup.complete'})
			elif message['type'] == 'lifespan.shutdown':
				# Clean up resources on shutdown
				try:
					from proxy.utils.proxy_manager import get_global_manager
					import logging
					logger = logging.getLogger('proxy')
					
					mgr = get_global_manager()
					if mgr:
						logger.info("ASGI shutdown: closing proxy manager...")
						await mgr.close()
						logger.info("ASGI shutdown: proxy manager closed")
				except Exception as e:
					import logging
					logging.getLogger('proxy').warning("ASGI shutdown: cleanup failed: %s", e)
				
				await send({'type': 'lifespan.shutdown.complete'})
				return
	else:
		# Forward all other requests to Django
		await django_app(scope, receive, send)