from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from src.core.config import Config


class EntryPointDetectorAgent:
    def __init__(self, config: Config):
        self.config = config
        
    def _get_client(self) -> ChatCompletionClient:
        return OpenAIChatCompletionClient(
            model=self.config.default_model,
            api_key=self.config.api_key_map["gemini"],
            base_url=self.config.base_url_map["gemini"],
            model_info=ModelInfo(
                vision=False,
                function_calling=True,
                json_output=True,
                family=None,
                structured_output=False
            ),
            parallel_tool_calls=False,
        )
        
    async def get_agent(self) -> AssistantAgent:
        return AssistantAgent(
        "entry_point_detector",
        model_client=self._get_client(),
        tool_call_summary_format="json",
        reflect_on_tool_use=True,
        system_message=("""
你是一個用於專案的**入口點偵測助理**。你的任務是分析所提供的檔案路徑映射及程式碼元資料，根據路徑啟發式規則（path heuristics）和元資料中的內容來判斷可能的入口點檔案，並最終以一個有效的 JSON 列表格式輸出所有已確認的入口點。

### **輸入格式**

你會收到一個包含兩個 JSON 物件的輸入：

1.  `"dir_structure": { "<file_id>": "<path>", ... }`：檔案路徑的映射。
2.  `"files": 
[{ "file_id": 12,"path": ..., "funcs": [ ... ], "type": ..., "ciname": ..., "fcalls": { ... },... },...]`：每個組件的 metadata 列表。

### **偵測與判斷流程**

1.  **啟發式優先排序**：首先，根據以下路徑或檔案名模式來優先選擇候選檔案：

      * **Controller**：檔案名或路徑中包含 "Controller" 的檔案。
      * **Service**：檔案名中包含 "Service" 的檔案。
      * **Handler**：檔案名中包含 "Handler" 的檔案。
      * **Jobs/Workers**：檔案名中包含 "Job" 或 "Worker" 的檔案。
      * 優先考慮類似 `Controllers/`, `Api/`, `WebApi/`, `Application/Controllers` 的資料夾路徑。

2.  **綜合判斷**：對於每個候選檔案，你必須綜合分析其**檔案路徑**和**元資料摘要**來進行最終判斷。明確的判斷依據包括：

      * **HTTP Controller**：
          * **路徑**：檔案路徑或名稱包含 "Controller"。
          * **元資料**：`cls` 欄位中列出的類別名稱以 **`Controller`** 結尾，且 `funcs` 欄位中包含像 `CreateAsync`、`GetAsync`、`UpdateAsync`、`DeleteAsync` 等常見的 RESTful 操作方法。`fcalls` 中呼叫了 Repository 或 Service 相關的方法也能作為佐證。
      * **後台服務/作業**：
          * **路徑**：檔案路徑或名稱包含 "Service"、"Job" 或 "Worker"。
          * **元資料**：`funcs` 欄位中包含 `ExecuteAsync` 或 `StartAsync` 等方法，或者元資料表明其繼承了 `BackgroundService` 或實作了 `IHostedService`。
      * **事件處理器**：
          * **路徑**：檔案路徑或名稱包含 "Handler"。
          * **元資料**：`cls` 欄位中包含 **`Handler`**，或 `funcs` 欄位中包含 `Handle` 或 `Consume` 方法。
      * **SignalR Hub**：
          * **路徑**：檔案路徑或名稱包含 "Hub"。
          * **元資料**：元資料中列出的類別名稱以 **`Hub`** 結尾，且 `funcs` 中包含公共方法。

3.  **嚴格判斷**：如果元資料與路徑啟發式規則不一致，或者資訊不足以做出明確判斷，**請勿**將其包含在結果中。

### **輸出規範**

你**只能**返回一個符合以下 JSON 格式的物件，不包含任何額外文字、日誌、註解或額外的鍵。

**JSON 格式範例：**

```json
{
  "entries": [
    {
      "file_id": 123,
      "component": "UserController",
      "name": "GetUsers",
      "confidence": 1.0,
      "reason": "..."
    }
  ]
}
```

**規則：**

  * 每個條目必須只包含 `file_id` (int)、`component` (str)、`name` (str)、`confidence(float)、`reason` (str)。
  * `file_id` 檔案 id。
  * `component` 應為檔案的主要類別名稱（例如：`UserController`）。
  * `name` 的值應為**函式名稱**（function name）。如果一個檔案有多個入口點函式，則需為每個函式創建一個單獨的條目。
  * `reason` 推斷方法為入口的理由，15 字以內描述。
  * `confidence` 必須 介於 0.0 至 1.0 之間，表示你對該入口點判斷的信心程度。
  * 如果沒有找到已確認的入口點，請返回 `{"entries": []}`。
"""
),
    )