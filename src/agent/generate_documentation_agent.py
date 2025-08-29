from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from src.core.config import Config
from src.entity.feature_analysis_entity import FeatureAnalysisEntity

class GenerateDocumentationAgent:
    def __init__(self, config: Config, run_id: str):
        self.config = config
        self.run_id = run_id
        
    def _get_client(self) -> ChatCompletionClient:
        return OpenAIChatCompletionClient(
            model=self.config.default_model,
            api_key=self.config.api_key_map["gemini"],
            base_url=self.config.base_url_map["gemini"],
            model_info=ModelInfo(
                vision=False,
                function_calling=False,
                json_output=False,
                family=None,
                structured_output=False
            ),
            parallel_tool_calls=False,
        )
        
    
    async def get_agent(self, component_name:str, func_name: str, lang:str) -> AssistantAgent:
        if (not func_name) or (not component_name):
            raise ValueError("Function / component name is required to create GenerateDocumentationAgent")
        
        ent = FeatureAnalysisEntity()
        
        return AssistantAgent(
            name=f"generate_documentationP_agent",
            model_client=self._get_client(),
            tool_call_summary_format="markdown",
            system_message=f"""你是一位資深的系統架構師與技術文件撰寫專家，擅長將複雜的系統架構與 API 呼叫流程轉換成清晰易懂的{lang}企業級技術文件。
## 任務目標
根據輸入的 JSON 功能分析資料，生成一份完整的 {lang} 「生產呼叫與資料流參考手冊」Markdown 文件。

## 輸入資料結構
{ent.model_json_schema()}

## 輸出要求
請將輸出結果組織為 Markdown 文件，並遵循以下結構（若特定段落無資料，則不輸出該段落），不要輸出額外的描述：
```
# {component_name}.{func_name}

**功能概述**
[summary 內容，保留粗體標記作為重點]

## **技術實作流程**

1. [依輸入整理的流程步驟]
2. [...]

**流程圖**
[嵌入 Mermaid 流程圖]

---

## 資料存取
* **讀取**: [table_read]
* **寫入**: [table_write]
| 資料表名稱 | 讀取功能 | 寫入功能 |
| ----- | ---- | ---- |

## 外部服務呼叫清單
[列出 external_api，包含服務名稱、端點、HTTP方法]
| 服務名稱 | HTTP方法 | 端點 | 使用功能 | 備註 |
| ---- | ------ | -- | ---- | -- |

```

## 特殊處理規則
- **table_read / table_write 為 null** → 該段落不輸出  
- **external_api 為 null** → 不輸出外部服務呼叫段落  
- **缺少對應流程圖** → 不輸出該功能的流程圖  
- **圖表與資料不一致** → 優先使用 summary 資料  
- **複雜呼叫鏈** → 提供簡化版與詳細版兩種說明  
""")