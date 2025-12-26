import json
from datetime import datetime
from typing import Optional

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema


def _parse_time(value: str) -> Optional[datetime]:
    if not value:
        return None
    # try ISO formats first (allow trailing Z)
    try:
        v = value
        if v.endswith('Z'):
            v = v[:-1] + '+00:00'
        return datetime.fromisoformat(v)
    except (ValueError, TypeError):
        # not ISO format
        pass
    # fallback known formats
    for fmt in ("%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


class LogsAPIView(APIView):
    """API to query JSON-lines log file with time filtering and pagination.

    Behaviors:
      - `limit` default/cap is taken from `settings.REST_FRAMEWORK['PAGE_SIZE']`.
      - `offset` for paging.
      - `start` / `end` accept ISO timestamps (or a couple common formats).
      - `query` substring search on message.
      - `level` exact match on level name.
    """

    def get(self, request):
        source = request.query_params.get('source', 'django')
        if source == 'proxy':
            path = getattr(settings, 'PROXY_LOG_JSON_PATH', None)
            if not path:
                return Response({"detail": "PROXY_LOG_JSON_PATH not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            path = getattr(settings, 'LOG_JSON_PATH', None)
            if not path:
                return Response({"detail": "LOG_JSON_PATH not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # page size default / cap from REST_FRAMEWORK
        page_size = 100
        rf = getattr(settings, 'REST_FRAMEWORK', {}) or {}
        try:
            page_size = int(rf.get('PAGE_SIZE', page_size))
        except Exception:
            page_size = page_size

        try:
            limit = int(request.query_params.get('limit', page_size))
        except Exception:
            limit = page_size
        # cap limit to page_size to avoid too large responses
        if limit <= 0:
            limit = page_size
        if limit > page_size:
            limit = page_size

        try:
            offset = int(request.query_params.get('offset', 0))
        except Exception:
            offset = 0
        if offset < 0:
            offset = 0

        level = request.query_params.get('level')
        query = request.query_params.get('query')
        # start/end time fields are optional; already parsed below
        start = _parse_time(request.query_params.get('start', ''))
        end = _parse_time(request.query_params.get('end', ''))

        results = []
        matched = 0
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        # skip non-json lines
                        continue

                    msg = obj.get('message') or obj.get('msg') or ''
                    lvl = obj.get('levelname') or obj.get('level') or ''
                    ts_raw = obj.get('asctime') or obj.get('timestamp')
                    ts = None
                    if ts_raw:
                        ts = _parse_time(ts_raw)

                    if level and lvl and lvl.upper() != level.upper():
                        continue
                    if query and query.lower() not in msg.lower():
                        continue
                    if start and ts and ts < start:
                        continue
                    if end and ts and ts > end:
                        continue

                    matched += 1
                    # collect only the requested page window
                    if matched > offset and len(results) < limit:
                        results.append({
                            'timestamp': ts_raw,
                            'level': lvl,
                            'logger': obj.get('name'),
                            'module': obj.get('module'),
                            'process': obj.get('process'),
                            'thread': obj.get('thread'),
                            'message': msg,
                            'raw': obj,
                        })
        except FileNotFoundError:
            return Response({"detail": f"Log file not found: {path}"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'count': matched,
            'offset': offset,
            'limit': limit,
            'results': results,
        })


class LogEntrySerializer(serializers.Serializer):
    timestamp = serializers.CharField(allow_null=True)
    level = serializers.CharField(allow_null=True)
    logger = serializers.CharField(allow_null=True)
    module = serializers.CharField(allow_null=True)
    process = serializers.CharField(allow_null=True)
    thread = serializers.CharField(allow_null=True)
    message = serializers.CharField(allow_null=True)
    raw = serializers.DictField()


class LogListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    offset = serializers.IntegerField()
    limit = serializers.IntegerField()
    results = LogEntrySerializer(many=True)


# Help drf-spectacular infer the response schema
LogsAPIView.serializer_class = LogListSerializer
LogsAPIView.get = extend_schema(responses=LogListSerializer)(LogsAPIView.get)