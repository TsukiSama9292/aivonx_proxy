# Ollama 反向代理
## 伺服器 API
1. [CRUD] Ollama 節點
2. [U] 調整負載平衡/HA策略
## 反向 API 列表
1. 健康情況:
  - 請求路徑: api/proxy
  - 根據當前是否有節點為可用狀態
  - 若有可用節點
    - 回傳狀態200、字串 Ollama is running
  - 若沒有可用節點
    - 回傳狀態404
2. 列出模型 API
  - 請求路徑: api/proxy/tags
  - 基於所有節點的可用模型回傳
3. Chat API, Generate API, Embed API, Embeddings API
  - 請求路徑: api/proxy/chat, api/proxy/generate, api/proxy/embed, api/proxy/embeddings
  - 需要節點有該可用模型
  - 執行反向代理策略
## 負載平衡策略
- 策略 1 : 自動依照當前活躍任務平均 ( 可調權重 )
- 策略 2 : 自動依照網路延遲分配
## HA 策略
1. 伺服器自動請求 Ollama 健康情況 API 檢查狀態
2. 處於離線狀態就移動到待機池
   - 每 10 分鐘再次請求一次，若為健康再移動回請求池
## 需要可慮
1. Ollama 有些不需要反向代理或是需要另外處理，需要直接請求，可以寫在 utils/ollama.py