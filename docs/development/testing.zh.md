# 測試

Aivonx Proxy 的全面測試指南。

## 執行測試

專案包含位於 `src/*/tests/` 的 pytest 配置的單元測試。

### Django 測試執行器

```bash
# 執行所有測試
python src/manage.py test proxy.tests account.tests logviewer.tests --verbosity 1 --keepdb
```