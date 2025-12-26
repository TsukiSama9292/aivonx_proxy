# 測試

Aivonx Proxy 的完整測試指南。

## 執行測試

專案包含以 pytest 與 Django test runner 為基礎的單元測試，檔案位於 `src/*/tests/`。

### Django 測試指令

```bash
# 執行所有測試
python src/manage.py test

# 執行特定 app
python src/manage.py test proxy

# 平行執行
python src/manage.py test --parallel
```

### pytest（可選）

```bash
# 執行 pytest
pytest

# 產生 coverage 報告
pytest --cov=src --cov-report=html
```

## 測試設定

測試會使用 `src/aivonx/settings.py` 的測試設定。在 CI 中請使用獨立的測試資料庫與 Redis 實例。

### 測試環境設定

測試期間，為加速執行，日誌等級通常設定為 ERROR 或以上。

## 測試結構

測試按應用分門別類：

```
src/
├── proxy/tests/          # Proxy 測試
│   ├── conftest.py      # pytest fixtures
│   └── test_*.py        # 測試模組
├── account/tests.py     # Account 測試
└── logviewer/tests.py   # Logviewer 測試
```

## 最佳實務

- 為新功能撰寫測試
- 在提交前確保既有測試通過
- 使用 fixtures 重複使用測試資料
- 模擬外部服務
- 測試邊緣案例與錯誤處理

## 覆蓋率

```bash
# 產生覆蓋率報表
coverage run --source='src' src/manage.py test
coverage report
coverage html
```