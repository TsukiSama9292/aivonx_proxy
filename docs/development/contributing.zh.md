# 貢獻指南

我們歡迎對 Aivonx Proxy 的貢獻！以下是如何開始。

## 開始使用

1. **Fork 儲存庫**
   - 在 GitHub 上 Fork 專案
   - 本地克隆您的 Fork
   ```bash
   git clone https://github.com/YOUR_USERNAME/aivonx_proxy.git
   cd aivonx_proxy
   ```

2. **設定開發環境**
   ```bash
   # 安裝依賴
   uv sync
   
   # 執行遷移
   uv run src/manage.py migrate
   
   # 建立超級使用者
   uv run src/manage.py createsuperuser
   ```

3. **建立功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 開發工作流程

### 執行測試

在提交更改之前，請確保所有測試通過：

```bash
# 執行所有測試
python src/manage.py test

# 執行特定應用程式測試
python src/manage.py test proxy

# 使用覆蓋率執行
coverage run --source='.' src/manage.py test
coverage report
```

### 程式碼風格

- 遵循現有的程式碼風格和慣例
- 使用有意義的變數和函數名稱
- 為新函數和類別新增文件字串
- 保持函數專注和模組化

### 進行更改

1. 在您的功能分支中進行更改
2. 根據需要編寫或更新測試
3. 如有必要，更新文件
4. 執行測試以確保一切正常
5. 使用清晰、描述性的訊息提交

```bash
git add .
git commit -m "[Types] description of changes"
```

類型：`[update]`、`[fix]`、`[tests]`、`[docs]`

## 提交拉取請求

1. **推送至您的 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **建立拉取請求**
   - 前往 GitHub 上的原始儲存庫
   - 點擊 "New Pull Request"
   - 選擇您的分支
   - 使用以下內容填寫 PR 模板：
     - 更改描述
     - 動機和背景
     - 相關問題編號
     - 執行的測試

3. **PR 審核流程**
   - 維護者將審核您的 PR
   - 處理任何回饋或請求的更改
   - 一旦批准，您的 PR 將被合併

## 指南

### 程式碼品質

- 編寫乾淨、可讀的程式碼
- 遵循 Django 和 Python 最佳實務
- 避免不必要的複雜性
- 保持提交原子化和專注

### 文件

- 更新相關文件
- 為公開 API 新增文件字串
- 如適用，更新 CHANGELOG
- 為新功能包含範例

### 測試

- 為新功能編寫測試
- 確保現有測試通過
- 致力於良好的測試覆蓋率
- 測試邊緣情況和錯誤條件

### 提交訊息

遵循慣例提交格式：

```
- 描述 1
- 描述 2
- 描述 3
```

## 貢獻什麼

### 好的首次問題

- 文件改進
- 錯誤修復
- 測試覆蓋率改進
- 程式碼註釋和澄清

### 功能請求

- 先開啟問題進行討論
- 在實作前獲得回饋
- 確保它符合專案目標

### 錯誤報告

報告錯誤時，請包含：
- 問題的清晰描述
- 重現步驟
- 預期與實際行為
- 環境詳細資訊（作業系統、Python 版本等）
- 相關日誌或錯誤訊息

## 行為準則

- 尊重和專業
- 歡迎新手
- 提供建設性回饋
- 專注於合作

## 有問題嗎？

如果您有問題：
- 檢查現有文件
- 搜尋已關閉的問題
- 開啟新問題進行討論
- 加入社群討論

感謝您的貢獻！