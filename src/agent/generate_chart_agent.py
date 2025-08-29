from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from src.core.config import Config
from src.entity import ChartEntity

class GenerateChartAgent:
    def __init__(self, config: Config, lang: str):
        self.config = config
        self.lang = lang
        
    def _get_client(self) -> ChatCompletionClient:
        return OpenAIChatCompletionClient(
            model=self.config.default_model,
            api_key=self.config.api_key_map["gemini"],
            base_url=self.config.base_url_map["gemini"],
            model_info=ModelInfo(
                vision=False,
                function_calling=False,
                json_output=True,
                family=None,
                structured_output=True
            ),
            parallel_tool_calls=False,
        )
        
    
    async def get_agent(self, component_name:str, func_name: str) -> AssistantAgent:
        if (not func_name) or (not component_name):
            raise ValueError("Function / component name is required to create GenerateDocumentationAgent")
        
        return AssistantAgent(
            name=f"generate_documentationP_agent",
            model_client=self._get_client(),
            tool_call_summary_format="markdown",
            output_content_type=ChartEntity,
            system_message=f"""你是一位熟練的 Mermaid 流程圖設計師，專門將方法呼叫鏈轉換成流程圖。
## 任務
- 根據輸入的 JSON 生成一個{self.lang}的 Mermaid 流程圖
- 流程圖必須可直接渲染，語法正確
- 所有節點以簡潔的英文 ID 表示（如 S1、S2...）
- 節點標籤格式：依照「組件名稱 - 方法名稱」格式顯示
- 若有 `data_access` 則在該節點之後加上資料庫節點，格式：「資料表名稱 - 操作類型」
- 若為 API 呼叫，節點標籤顯示「服務名稱 - API呼叫」
- **[]括號中絕對不可以出現()括號與{{}}括號**
    - S5 -->|Read| S5_DB[sModel (ElasticSearch) - Read] (ElasticSearch) 括號會造成錯誤，不要做
    - S0[HTTP GET - /service/get/{{communityId}}] {{communityId}} 括號會造成錯誤，不要做, 不加括號顯示即可 S0[HTTP GET - /service/get/communityId]

## Mermaid 規則
- 節點 ID 後不能有空格
- 節點標籤內允許空格，但避免特殊符號造成語法錯誤
- 每行連接格式為 `A --> B` 或 `A -->|標註| B`
- 不允許多餘的分號
""")