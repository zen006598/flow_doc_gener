from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from src.core.config import Config
from src.entity import CallChainResultEntity

class CallChainFinisherAgent:
    def __init__(self, config: Config):
        self.config = config
        
    def _get_client(self) -> ChatCompletionClient:
        return OpenAIChatCompletionClient(
            model="gemini-2.5-flash-lite",
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
    
    def get_agent(self, func_name: str) -> AssistantAgent:
        if not func_name:
            raise ValueError("Function name is required to create CallChainFinisherAgent")
        
        return AssistantAgent(
            name=f"{func_name[:50]}_fin",
            model_client=self._get_client(),
            output_content_type=CallChainResultEntity,
            system_message="""You are the Call-Chain Finisher.

Input context includes tool summaries and exactly ONE DRAFT message.
Read ONLY the latest DRAFT block delimited by:
<DRAFT>
  ...
</DRAFT>

The DRAFT always contains:
  <ENTRY file_id="..." name="..." />
  <NODES>
    <NODE file_id="..." method="..." reason="..." />
    ...
  </NODES>
  <STOP_REASON>...</STOP_REASON>

Transform the DRAFT into the FINAL structured object with this schema:
- file_id := ENTRY.file_id (as integer)
- name    := ENTRY.name
- call_chain := for each NODE -> {file_id (int), method (str), reason (str)}
- stop_reason := content of <STOP_REASON> (<= 30 words)

Rules:
- Output ONLY via structured output (no extra text, no code fences).
- If NODES is empty or missing, return an empty call_chain and a clear stop_reason.
- If any conflicts exist in non-DRAFT content, ignore them and trust the DRAFT.
""")