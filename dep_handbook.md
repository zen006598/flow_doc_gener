# 相依性分析資料使用手冊

## 資料架構說明

相依性分析結果JSON包含兩個主要部分：

### 1. files 檔案資訊

每個檔案都有一個唯一的 `file_id` 作為識別，包含以下資訊：

```json
{
  "files": {
    "<file_id>": {
      "path": "檔案路徑",
      "funcs": ["函數名稱列表"],
      "cls": ["類別名稱列表"],
      "calls": ["對外呼叫的簡化名稱"],
      "fcalls": { 
        "<函數名>": [ 
          { 
            "method": "<被呼叫者>", 
            "expr": "<呼叫表達式>" 
          } 
        ] 
      }
    }
  }
}
```

#### 欄位說明：

- **path**: 檔案的完整路徑
- **funcs**: 該檔案中定義的所有函數名稱
- **cls**: 該檔案中定義的所有類別名稱
- **calls**: 該檔案對外呼叫的函數名稱（簡化版）
- **fcalls**: 詳細的函數呼叫資訊，包含呼叫者、被呼叫者及呼叫表達式

### 2. deps 相依性關係

描述函數層級的相依性關係：

```json
[
  {
    "from": "<來源檔案ID>",
    "from_func": "<呼叫者函數>",
    "to": "<目標檔案ID>",
    "to_func": "<被呼叫函數>",
    "call": {
      "method": "<被呼叫者>", 
      "expr": "<呼叫表達式>"
    }
  }
]
```

#### 欄位說明：

- **from**: 發起呼叫的檔案ID
- **from_func**: 發起呼叫的函數名稱
- **to**: 被呼叫的目標檔案ID
- **to_func**: 被呼叫的目標函數名稱
- **call**: 呼叫的詳細資訊

## 使用規則

### 檔案資訊查詢 (files)

1. **路徑分析**: 使用 `files[file_id].path` 來判斷檔案類型
   - 包含 `/Controllers/` 或 `\\Controllers\\` → MVC控制器
   - 包含 `/Services/` 或 `\\Services\\` → 服務層
   - 包含 `/Repository/` 或 `\\Repository\\` → 資料存取層
   - 包含 `/Models/` 或 `\\Models\\` → 資料模型
   - 包含 `/Infrastructure/` → 基礎設施層
   - 檔案名稱包含 "Background", "Job", "Worker" → 背景作業

2. **類別分析**: 使用 `files[file_id].cls` 來識別該檔案中定義的類別
   - 類別名稱結尾為 "Controller" → MVC控制器
   - 類別名稱包含 "Service" → 服務層
   - 類別名稱包含 "Repository" → 資料存取層
   - 類別名稱包含 "Handler", "Consumer" → 事件處理器
   - 類別名稱包含 "Validator" → 驗證邏輯
   - 類別名稱包含 "Mapper", "Profile" → 物件對應

3. **函數分析**: 使用 `files[file_id].funcs` 來識別該檔案中定義的函數,
   - "Main" → 程式進入點
   - "Execute", "ExecuteAsync" → 背景作業

4. **呼叫分析**: 使用 `files[file_id].calls` 來識別該檔案中有呼叫到的方法, 簡化版的方法呼叫列表，用於快速檢查
   - MapGet, MapPost, MapPut, MapDelete → Minimal API
   - AddGrpc, MapGrpcService → gRPC服務
  
5. **函數呼叫詳細分析** (`files[file_id].fcalls`) 提供每個函數內部的詳細呼叫資訊：
- 結構說明：
```json
"fcalls": {
  "函數名稱": [
    {
      "method": "被呼叫的方法名",
      "expr": "完整的呼叫表達式"
    }
  ]
}
- **函數內部邏輯分析**：了解每個函數具體做了什麼
- **呼叫模式識別**：
  - 多次呼叫同一個 Repository 方法 → 資料存取邏輯
  - 呼叫多個不同 Service → 複雜業務邏輯
  - 呼叫 FindByIdAsync 後接其他操作 → 典型的查詢-操作模式

### 相依性關係查詢 (deps)

1. **向上追蹤**: 找出誰呼叫了某個函數
   - 篩選 `deps` 陣列中 `to` 等於目標檔案ID 且 `call.method` 等於目標函數的項目

2. **向下追蹤**: 找出某個函數呼叫了哪些其他函數
   - 篩選 `deps` 陣列中 `from` 等於來源檔案ID 且 `from_func` 等於來源函數的項目

3. **信心度提升**: 結合 files 和 deps 資訊
   - 如果某個函數在 `deps` 中作為 `from_func` 出現，且其所屬檔案符合進入點規則，則提高信心度
  - 如果 `deps` 中的呼叫模式與 `fcalls` 中的詳細資訊一致，則提高準確性
  - 如果呼叫鏈符合典型的架構層級順序（Controller → Service → Repository），則提高可信度
## 進入點識別規則

### A. HTTP控制器 (ASP.NET / MVC)
- 檔案路徑包含 "/Controllers/" 或 "\\Controllers\\"，或任何類別名稱以 "Controller" 結尾
- 該檔案中列出的所有函數都是候選控制器動作

### B. Minimal API (Program.cs / Startup)
- 檔案呼叫包含: MapGet, MapPost, MapPut, MapDelete, MapPatch, MapGroup, MapControllerRoute
- 為每個 Map* 出現記錄一個進入點

### C. 背景作業 / 排程器
- 類別名稱或檔案路徑暗示 "Job", "Quartz", "Hangfire", "Worker", "HostedService", "BackgroundService"
- Execute/ExecuteAsync/Run 等函數為進入點

### D. 事件/佇列消費者
- 類別名稱包含 "Handler", "Consumer", "Subscriber", "Listener", "Receiver"
- Handle/Consume/OnMessage/Process 等函數為進入點

### E. CLI / 批次處理
- 函數包含 "Main" 或檔案路徑暗示控制台工具

### F. RPC / gRPC / GraphQL
- 類別名稱以 "Service" 結尾配對框架信號 (如 AddGrpc, MapGrpcService)
- 類別名稱為 "Query" 或 "Mutation" → GraphQL resolver

## 注意事項

- 優先考慮召回率（包含而非排除）
- 根據 (path, component, name) 去重複
- 缺少組件時標記為 "[unknown]"
- 當僅有弱信號存在時保持保守的信心度