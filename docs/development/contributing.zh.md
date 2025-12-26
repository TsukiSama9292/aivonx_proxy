# 貢獻指南

歡迎為 Aivonx Proxy 做出貢獻！以下說明如何開始。

## 快速開始

1. **Fork 專案**
   - 在 GitHub 上 fork 本專案
   - 將 fork clone 到本機
   ```bash
   git clone https://github.com/YOUR_USERNAME/aivonx_proxy.git
   cd aivonx_proxy
   ```

2. **設定開發環境**
   ```bash
   # 安裝相依
   uv sync
   
   # 執行 migrations
   uv run src/manage.py migrate
   
   # 建立 superuser
   uv run src/manage.py createsuperuser
   ```

3. **建立功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 開發流程

### 執行測試

提交前請確保測試皆通過：

```bash
# 執行全部測試
python src/manage.py test

# 執行特定 app 測試
python src/manage.py test proxy

# 使用 coverage
coverage run --source='.' src/manage.py test
coverage report
```

### 程式風格

- 遵循既有風格與命名慣例
- 使用具意義的變數與函式名稱
- 新增函式/類別請加入 docstring
- 保持函式單一責任與易維護

### 提交變更

1. 在功能分支完成修改
2. 適當新增或更新測試
3. 更新文件（如有需要）
4. 執行測試
5. 使用清晰訊息 commit

```bash
git add .
git commit -m "Add feature: description of changes"
```

## 提交 Pull Request

1. **推送到你的 fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **建立 PR**
   - 前往原始專案頁面
   - 點選 "New Pull Request"
   - 選取你的分支並填寫 PR 範本：
     - 變更描述
     - 動機與背景
     - 相關 issue 編號
     - 已做測試

3. **審查流程**
   - 維護者會檢視 PR
   - 回應修改意見並更新 PR
   - 經批准後合併

## 指南

### 程式品質

- 撰寫清晰可讀程式碼
- 遵循 Django 與 Python 最佳實務
- 避免不必要複雜度
- 保持 commits 原子性

### 文件

- 更新相關文件
- 新增公開 API 的 docstring
- 如有必要更新 CHANGELOG

### 測試

- 為新功能新增測試
- 確保既有測試通過
- 盡量涵蓋邊緣案例

### Commit 訊息

採用 conventional commit 格式：

```
type(scope): brief description

Detailed explanation if needed

Fixes #issue_number
```

型別範例：`feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## 可貢獻項目

### 適合新手的 issue

- 文件改進
- 小型 bug 修正
- 測試覆蓋率提升
- 註解或程式碼清理

### 功能需求

- 先開 issue 討論
- 征求回饋後再實作
- 確認與專案目標一致

### Bug 回報

回報時請包含：
- 問題描述
- 重現步驟
- 預期與實際行為
- 執行環境（OS、Python 版本）
- 相關日誌或錯誤訊息

## 行為準則

- 保持尊重與專業
- 歡迎新手貢獻
- 提供建設性回饋
- 以合作為優先

謝謝你的貢獻！