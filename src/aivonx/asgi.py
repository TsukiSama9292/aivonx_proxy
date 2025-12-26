import os
import asyncio
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
					# Ollama exposes a base-url health response (e.g. GET http://host:port -> "ollama is running");
					# use empty health_path so manager will probe the node root.
					mgr = HAProxyManager(nodes=None, health_path="")
					
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
					# Use leader lock to ensure only one worker starts the scheduler
					try:
						from django.core.cache import cache
						leader_key = "ha_manager_leader"
						leader_lock_timeout = 30  # 30 seconds (short TTL with renew)
						# Info: report cache backend and current leader key state (use INFO to ensure visibility)
						backend = cache.__class__.__module__ + "." + cache.__class__.__name__
						logger.info("ASGI startup: cache backend = %s", backend)
						try:
							existing = cache.get(leader_key)
							logger.info("ASGI startup: leader key exists before add = %s", existing is not None)
						except Exception:
							logger.info("ASGI startup: unable to read leader key before add")
					
						# Try to acquire distributed leader lock (atomic on Redis/Memcached)
						got_lock = False
						try:
							got_lock = cache.add(leader_key, True, leader_lock_timeout)
							logger.info("ASGI startup: cache.add returned = %s", got_lock)
						except Exception as add_error:
							logger.exception("ASGI startup: cache.add failed with exception: %s", add_error)
							got_lock = False

						# If cache.add succeeded, try to ensure Redis also has an owner value
						if got_lock:
							try:
								import socket
								owner = f"{socket.gethostname()}:{os.getpid()}"
								try:
									from django_redis import get_redis_connection
									conn = get_redis_connection('default')
									val = conn.get(leader_key)
									if val is None:
										try:
											conn.set(leader_key, owner, ex=leader_lock_timeout)
										except Exception as e:
											logger.debug("ASGI startup: failed to write owner to redis after cache.add: %s", e)
								except Exception as e:
									logger.debug("ASGI startup: redis owner read/write path failed: %s", e)
							except Exception:
								logger.debug("ASGI startup: owner write skipped (socket/import failed)")

						# If cache.add did not acquire the lock, try raw Redis SET NX (if django-redis available).
						# This avoids issues with local in-process proxies/local cache layers.
						if not got_lock:
							try:
								import socket
								owner = f"{socket.gethostname()}:{os.getpid()}"
								from django_redis import get_redis_connection
								conn = get_redis_connection('default')
								# Use process id as value for debugging
								redis_set = conn.set(leader_key, owner, nx=True, ex=leader_lock_timeout)
								logger.info("ASGI startup: raw redis SET NX returned = %s", redis_set)
								if redis_set:
									# ensure Django cache layer reflects the lock too
									try:
										cache.set(leader_key, True, leader_lock_timeout)
									except Exception:
										logger.debug("ASGI startup: failed to set leader key in cache layer after redis set")
									got_lock = True
							except Exception as e:
								logger.debug("ASGI startup: raw redis SET NX attempt failed: %s", e)

						# If we've acquired the lock, set up a renew (heartbeat) loop and store owner id on mgr
						if got_lock:
							# determine owner id
							import socket
							owner = f"{socket.gethostname()}:{os.getpid()}"
							# attach owner to manager for shutdown/inspection
							try:
								mgr._leader_owner = owner
							except Exception as e:
								logger.debug("ASGI startup: failed to attach _leader_owner to manager: %s", e)
							# ensure redis conn exists for renew loop
							try:
								from django_redis import get_redis_connection
								renew_conn = get_redis_connection('default')
							except Exception:
								renew_conn = None

							# start renew loop to extend TTL periodically
							async def _renew_loop(conn, key, owner_id, ttl, mgr_ref):
								interval = max(5, int(ttl / 2))
								try:
									while True:
										await asyncio.sleep(interval)
										try:
											if conn is None:
												# try to re-acquire a connection
												from django_redis import get_redis_connection as _grc
												conn = _grc('default')
											# check ownership
											val = conn.get(key)
											if val is None or val.decode() != owner_id:
												# lost ownership
												logger.info("Leader renew loop: lost ownership of key %s (val=%s)", key, val)
												break
											# extend TTL
											conn.expire(key, ttl)
										except Exception:
											logger.debug("Leader renew loop: renew attempt failed, will retry")
								except asyncio.CancelledError:
									logger.info("Leader renew loop cancelled for key %s", key)
									return
								logger.info("Leader renew loop exiting for key %s", key)
							# attach task and conn to mgr for cleanup
							try:
								mgr._leader_renew_task = asyncio.create_task(_renew_loop(renew_conn, leader_key, owner, leader_lock_timeout, mgr))
							except Exception:
								logger.debug("ASGI startup: failed to start leader renew task")
							# After acquiring lock, ensure this leader populates caches (DB refresh + health/models)
							try:
								logger.info("ASGI startup: leader acquired - performing post-lock refreshes")
								# refresh DB-backed node list (async)
								try:
									await mgr._refresh_from_db_async()
								except Exception:
									logger.debug("ASGI startup: _refresh_from_db_async failed after lock")
								try:
									await mgr.refresh_models_all()
								except Exception:
									logger.debug("ASGI startup: refresh_models_all failed after lock")
								try:
									await mgr.health_check_all()
								except Exception:
									logger.debug("ASGI startup: health_check_all failed after lock")
							except Exception:
								logger.debug("ASGI startup: post-lock refresh sequence failed")
					
						# If using django-redis, also inspect raw Redis key for TTL/value
						try:
							from django_redis import get_redis_connection
							conn = get_redis_connection("default")
							try:
								val = conn.get(leader_key)
								ttl = conn.ttl(leader_key)
								logger.info("ASGI startup: redis raw key val=%s ttl=%s", val, ttl)
							except Exception as e:
								logger.info("ASGI startup: redis key inspection failed: %s", e)
						except Exception as e:
							# not a django-redis backend or inspection failed
							logger.debug("ASGI startup: django-redis unavailable or inspection error: %s", e)
						
						if got_lock:
							try:
								mgr.start_scheduler(interval_seconds=10)
								logger.info("ASGI startup: ✅ acquired leader lock and started scheduler in this worker (PID %d)", os.getpid())
							except Exception as e:
								logger.exception("ASGI startup: scheduler start failed: %s", e)
								# Release lock on failure so another worker can try
								cache.delete(leader_key)
						else:
							logger.info("ASGI startup: ⏭️  did not acquire leader lock; scheduler not started in this worker (PID %d)", os.getpid())
					except Exception as e:
						logger.error("ASGI startup: leader lock check failed: %s", e, exc_info=True)

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
						# If this process held the leader lock, attempt to release it
						try:
							leader_key = "ha_manager_leader"
							owner = getattr(mgr, '_leader_owner', None)
							renew_task = getattr(mgr, '_leader_renew_task', None)
							if renew_task:
								try:
									renew_task.cancel()
								except Exception as e:
									logger.debug("ASGI shutdown: renew task cancel failed: %s", e)
							if owner:
								try:
									from django_redis import get_redis_connection
									conn = get_redis_connection('default')
									val = conn.get(leader_key)
									if val and val.decode() == owner:
										conn.delete(leader_key)
										try:
											from django.core.cache import cache
											cache.delete(leader_key)
										except Exception as e:
											logger.debug("ASGI shutdown: delete leader key from cache failed: %s", e)
									logger.info("ASGI shutdown: released leader lock (owner=%s)", owner)
								except Exception:
									logger.debug("ASGI shutdown: failed to release leader lock cleanly")
						except Exception:
							logger.debug("ASGI shutdown: leader lock release check failed")
						# Close manager resources
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