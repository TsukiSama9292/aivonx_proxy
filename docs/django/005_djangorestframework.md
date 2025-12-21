# djangorestframework

## 1. 修改 Django 設定檔案(`src/aivonx/settings.py`)

```python
INSTALLED_APPS = [
  # ...
  'rest_framework',
]
```

## 2. 依照需求調整 REST_FRAMEWORK 設定

```python
REST_FRAMEWORK = {
    "PAGE_SIZE": 100, # List API 支援分頁時，每頁只傳回 100 筆
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination", # 分頁的參數是使用 limit 跟 offset
    "DEFAULT_AUTHENTICATION_CLASSES": ( # 驗證方式
        "rest_framework.authentication.SessionAuthentication", # Session
        "rest_framework.authentication.TokenAuthentication", # Token
    ),
    "DEFAULT_PERMISSION_CLASSES": ( # 權限要求
        "rest_framework.permissions.IsAuthenticated", # 必須要驗證過才能呼叫 API
    ), 
}
```

## 3. 新增應用(`analyze`)

```bash
uv run manage.py startapp analyze
```

## 4. 修改 Django 設定檔案(`src/aivonx/settings.py`)

```python
INSTALLED_APPS = [
  # ...
  'analyze',
]
```

## 5. 定義模型(`src/analyze/models.py`)

```python
from django.db import models

class Reporter(models.Model):
    name = models.CharField(max_length=250)

class Article(models.Model):
    title = models.CharField(max_length=250)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reporter = models.ForeignKey(Reporter, on_delete=models.CASCADE)
```

## 6. 建立遷移檔案，並且執行遷移

```bash
uv run manage.py makemigrations
uv run manage.py migrate
```

## 7. 定義 Serializer (`src/analyze/serializers.py`)

```python
from rest_framework import serializers
from .models import Article

class ArticleSerializer(serializers.ModelSerializer):
  class Meta:
    model = Article
    fields = ['id', 'title', 'content', 'created_at', 'updated_at', 'reporter']
```

## 8. 定義 API，此處想要提供一整組，包含建立、修改、刪除、查詢等功能，所以可以直接使用 ModelViewSet (`src/analyze/viewsets.py`)

```python
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = (AllowAny,)
```

## 9. 定義 urls

```python
from .viewsets import ArticleViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')
urlpatterns = router.urls
```

## 10. 在專案的 urls 裡把上面的 urlpatterns 加進來 (`src/aivonx/urls.py`)

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/analyze/", include("analyze.urls")),
]
```