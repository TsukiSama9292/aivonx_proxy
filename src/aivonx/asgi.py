"""
ASGI config for aivonx project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aivonx.settings')

# application = get_asgi_application()

import os
from django_asgi_lifespan.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aivonx.settings')

# Wrap the ASGI application to run HA manager DB initialization on lifespan.startup
inner_app = get_asgi_application()


async def application(scope, receive, send):
	# handle lifespan events to initialize HA manager after Django is fully ready
	if scope['type'] == 'lifespan':
		while True:
			message = await receive()
			if message['type'] == 'lifespan.startup':
				try:
					# import here so Django is fully loaded
					from proxy.utils.proxy_manager import init_global_manager_from_db

					# Initialize manager and run initial refresh/health checks synchronously
					mgr = init_global_manager_from_db()
					# If manager exposes async methods, await them so cache is populated before serving
					try:
						await mgr.refresh_models_all()
					except Exception:
						pass
					try:
						await mgr.health_check_all()
					except Exception:
						pass
					# Start the background scheduler for periodic health checks and model refreshes
					try:
						mgr.start_scheduler(interval_minutes=10)
					except Exception:
						pass
				except Exception:
					# safe to ignore; manager can be initialized later
					pass
				await send({'type': 'lifespan.startup.complete'})
			elif message['type'] == 'lifespan.shutdown':
				await send({'type': 'lifespan.shutdown.complete'})
				return
	else:
		await inner_app(scope, receive, send)