# Ollama 反向代理
## 伺服器 API
1. [CRUD] Ollama 節點
2. [U] 調整負載平衡/HA策略
3. [CRUD] API 金鑰
## 反向 API 列表
1. 健康情況 API
2. 列出模型 API
3. 拉取模型 API
4. Chat API
5. Generate API
## 負載平衡策略
- 策略 1 : 自動依照當前活躍任務平均 ( 可調權重 )
- 策略 2 : 自動依照網路延遲分配
## HA 策略
1. 伺服器自動請求 Ollama 健康情況 API 檢查狀態
2. 處於離線狀態就移動到待機池
   - 每 10 分鐘再次請求一次，若為健康再移動回請求池
# Docker Swarm
...