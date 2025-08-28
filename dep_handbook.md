# 相依性分析資料使用手冊

## 資料架構說明

新版相依性分析結果包含兩個主要部分：

### 1. files 實體資訊 (List[FunctionAnalysisEntity])

每個實體代表一個檔案中的類別或命名空間，包含以下資訊：

#### 實體結構：
```json
{
  "file_id": 123,
  "path": "src/Controllers/UserController.cs", 
  "ciname": "UserController",
  "type": "class",
  "funcs": ["GetUser", "CreateUser", "UpdateUser"],
  "fcalls": {
    "GetUser": [
      {
        "method": "FindByIdAsync",
        "expr": "userRepository.FindByIdAsync(id)"
      }
    ],
    "CreateUser": [
      {
        "method": "ValidateUser", 
        "expr": "validator.ValidateUser(user)"
      },
      {
        "method": "SaveAsync",
        "expr": "userRepository.SaveAsync(user)"
      }
    ]
  }
}
```

#### 欄位說明：

- **file_id**: 檔案的識別ID（注意：不是唯一值，同一檔案中可能有多組 class/interface 實體）
- **path**: 檔案的完整路徑 
- **ciname**: 組件名稱，表示為 class / interface 等的具體名稱
- **type**: 實體類型，用於判斷組件是什麼（"class", "interface" 等）
- **funcs**: 該組件中定義的所有函數名稱列表，作為簡易查詢
- **fcalls**: 組件中所有 funcs 的詳細呼叫資訊，記錄每個 function 中出現的呼叫

### 2. deps 相依性關係 (List[DependencyEntity])

描述實體層級和函數層級的相依性關係：


#### 相依性結構：
```json
{
  "caller_file_id": 123,
  "caller_entity": "UserController", 
  "caller_func": "GetUser",
  "callee_file_if": 456,
  "callee_entity": "UserRepository",
  "call": {
    "method": "FindByIdAsync",
    "expr": "userRepository.FindByIdAsync(id)"
  }
}
```

#### 欄位說明：

- **caller_file_id**: 發起呼叫的檔案ID
- **caller_entity**: 發起呼叫的實體名稱
- **caller_func**: 發起呼叫的函數名稱
- **callee_file_if**: 被呼叫的目標檔案ID
- **callee_entity**: 被呼叫的目標實體名稱
- **call**: 呼叫的詳細資訊 (method, expr)

## 使用規則

### 檔案資訊查詢 (files)

1. **路徑分析 + 實體類型分析**: 使用 `entity.type` 判斷組件類型，`entity.path` 作為輔助
   - **主要判斷**: `entity.type` = "class", "interface", "enum" 等
   - **輔助判斷**: 路徑包含 `/Controllers/` 或 `\\Controllers\\` → MVC控制器相關
   - 路徑包含 `/Services/` 或 `\\Services\\` → 服務層相關
   - 路徑包含 `/Repository/` 或 `\\Repository\\` → 資料存取層相關
   - 路徑包含 `/Models/` 或 `\\Models\\` → 資料模型相關
   - 路徑包含 `/Infrastructure/` → 基礎設施層相關
   - 檔案名稱包含 "Background", "Job", "Worker" → 背景作業相關

2. **組件名稱分析**: 使用 `entity.ciname` 來識別組件的具體名稱和用途
   - 組件名稱結尾為 "Controller" → MVC控制器
   - 組件名稱包含 "Service" → 服務層
   - 組件名稱包含 "Repository" → 資料存取層
   - 組件名稱包含 "Handler", "Consumer" → 事件處理器
   - 組件名稱包含 "Validator" → 驗證邏輯
   - 組件名稱包含 "Mapper", "Profile" → 物件對應
   - 組件名稱以 "I" 開頭且 `type` = "interface" → 介面定義

3. **函數簡易查詢**: 使用 `entity.funcs` 快速了解組件中有哪些函數
   - "Main" → 程式進入點
   - "Execute", "ExecuteAsync" → 背景作業
   - HTTP動詞命名 (Get*, Post*, Put*, Delete*) → API端點
   - "Handle", "Consume", "Process" → 事件處理
   - "Validate" → 驗證邏輯

4. **函數呼叫詳細分析**: 使用 `entity.fcalls` 了解每個函數內部的呼叫細節
   - 結構說明：`fcalls` 記錄組件中所有 funcs 的呼叫資訊
   - 每個函數名對應該函數中出現的所有方法呼叫
   - 每個呼叫包含 `method`（被呼叫的方法名）和 `expr`（完整的呼叫表達式）
   - **呼叫模式識別**：
     - 多次呼叫帶有 "Repository" 的方法 → 資料存取邏輯
     - 呼叫多個不同帶有 "Service" 的方法 → 複雜業務邏輯
     - 包含 "Map*" 呼叫 → Minimal API 定義
     - 包含 "*Async" 呼叫 → 非同步處理模式

5. **檔案ID注意事項**: 
   - `file_id` 不是唯一值，同一檔案中可能包含多個組件（class, interface 等）
   - 相同 `file_id` 但不同 `ciname` 代表同一檔案中的不同組件
   - 查詢時需要同時考慮 `file_id` 和 `ciname` 來精確定位組件

### 相依性關係查詢 (deps)

1. **向上追蹤**: 找出誰呼叫了某個組件/函數
   - 使用 `callee_file_if`（被呼叫者檔案ID）定位目標檔案
   - 使用 `call.expr`（呼叫表達式）精確匹配特定的呼叫
   - 結果包含 `caller_entity`（呼叫者組件）和 `caller_func`（呼叫者函數）
   - 可以追蹤到是哪個組件的哪個函數發起了這個呼叫

2. **向下追蹤**: 找出某個組件/函數呼叫了誰
   - 使用 `caller_file_id`（呼叫者檔案ID）定位來源檔案
   - 使用 `call.expr`（呼叫表達式）了解具體呼叫了什麼
   - 結果包含 `callee_entity`（被呼叫者組件）和 `call.method`（被呼叫的方法）
   - 可以了解某個組件的對外相依性

3. **精確追蹤**: 結合檔案ID和表達式進行精確查詢
   - 根據特定的 `call.expr` 表達式追蹤呼叫流向
   - 可以精確定位某個特定呼叫會影響哪些組件

4. **跨檔案分析**: 利用 `file_id` 追蹤跨檔案的相依關係
   - 比較 `caller_file_id` 和 `callee_file_if`，判斷是否為跨檔案呼叫
   - 結合組件的 `path` 資訊，可以分析跨專案、跨模組的相依關係
   - 識別不同架構層級之間的呼叫關係

5. **相依性分析規則**

**基本查詢原則**：
   - **完整匹配**: 使用完整的 `call.expr` 進行精確匹配，避免誤判
   - **檔案關聯**: 透過 `file_id` 建立檔案之間的相依關係網絡
   - **組件識別**: 結合 `caller_entity` 和 `callee_entity` 了解組件層級的相依關係

**呼叫模式識別**：
   - **直接呼叫**: `call.expr` 中直接包含方法名稱，表示直接的函數呼叫
   - **物件方法呼叫**: `call.expr` 中包含 `object.method()` 模式，表示透過物件實例呼叫
   - **靜態方法呼叫**: `call.expr` 中包含 `ClassName.method()` 模式，表示靜態方法呼叫
   - **鏈式呼叫**: `call.expr` 中包含多個 `.` 連接，表示方法鏈呼叫

### 綜合分析策略

**實體與相依性的交叉驗證**
   - 使用 `entities` 中的 `fcalls` 資訊與 `dependencies` 中的呼叫記錄進行比對
   - 如果某個組件的 `fcalls` 中包含特定方法呼叫，應該在 `dependencies` 中找到對應的相依關係記錄
   - 注意：同一 `file_id` 可能對應多個組件，需要透過 `ciname` 區分

**架構層級一致性檢查**
   - 根據組件的 `path` 和 `ciname` 判斷其架構層級
   - 結合 `type` 資訊確認組件類型（class, interface 等）
   - 檢查 `dependencies` 中的呼叫關係是否符合預期的架構設計

**進入點到終端點的完整追蹤**
   - 從識別出的進入點組件開始，透過 `dependencies` 遞歸追蹤整個呼叫鏈
   - 結合 `entities` 中的 `funcs` 和 `fcalls` 資訊，建立完整的執行流程圖
   - 使用 `call.expr` 進行精確的呼叫追蹤

