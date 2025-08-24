import json
from typing import Dict, Any

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import StructuredMessage, TextMessage

from src.core.config import Config
from src.agent.function_tool.dependency_tools import create_dependency_tools
from src.agent.function_tool.source_code_tools import create_source_code_tools
from src.model.call_chain_models import CallChainResult, EntryPoint


class CallChainAnalyzerService:
    """Service for analyzing function call chains using AI agents"""
    
    def __init__(self, config: Config, run_id: str):
        """
        Initialize the service
        
        Args:
            config: Configuration object containing API keys, models, etc.
            run_id: The run ID for loading cached data and tools
        """
        self.config = config
        self.run_id = run_id
        self.main_client = None
        self.lite_client = None
        self.dependency_tools = None
        self.source_code_tools = None
    
    async def _initialize(self):
        """Initialize clients and tools asynchronously"""
        if self.main_client is None:
            # Create main client for complex analysis
            self.main_client = OpenAIChatCompletionClient(
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
            
            # Create lite client for finishing tasks
            self.lite_client = OpenAIChatCompletionClient(
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
            
            self.dependency_tools = await create_dependency_tools(self.run_id)
            self.source_code_tools = await create_source_code_tools(self.run_id)
    
    def _create_finisher_agent(self, entry_name: str) -> AssistantAgent:
        """Create the finisher agent"""
        return AssistantAgent(
            name=f"{entry_name}_call_chain_finisher",
            model_client=self.lite_client,
            output_content_type=CallChainResult,
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
    
    def _create_analyzer_agent(self, entry_name: str) -> AssistantAgent:
        """Create the analyzer agent with tools"""
        agent_tools = [
            self.dependency_tools["get_function_snippet"],
            self.dependency_tools["get_deps_by_file_id_and_expr"],
            self.dependency_tools["get_deps_to"],
            self.source_code_tools["get_file_content"]
        ]
        
        return AssistantAgent(
            name=f"{entry_name}_call_chain_analyzer",
            model_client=self.main_client,
            tools=agent_tools,
            max_tool_iterations=60,
            tool_call_summary_format="json",
            reflect_on_tool_use=True,
            system_message="""You are **Call-Chain Agent — End-to-End Function Call Tracer**.  
Your mission: **discover the complete function call chain for a given entry point**, using the provided metadata and tools to trace calls across files and layers **until no further calls are found**, then return the **entire call_chain**.

---

## INPUT
```json
{
  "entry_point": {
    "name": "<function_name>",
    "component": "<class_or_component>",
    "file_id": <file_id>
  }
}
````

* **name**: the entry function to analyze
* **component**: the class/component containing the entry function
* **file_id**: ID of the file containing the entry function

---

## TOOLS (use strictly, do not fabricate results)

* **get_function_snippet(file_id, function_name)**:
  Returns internal calls (methods + expressions) within a specific function.
  *Use to find what the function itself calls.*

* **get_deps_by_file_id_and_expr(file_id, expr)**:
  Returns a list of target file_ids matching a specific call expression from a given file.
  *Use to find where a specific call expression resolves.*

* **get_deps_to(file_id)**:
  Returns who calls this file and its functions.
  *Use only when upward-tracing is required (who uses this file).*

* **get_file_content(file_id)**:
  Returns full source code for a file.
  *Use only when metadata is insufficient to confirm a match.*

---

## WORKFLOW (follow exactly)

### 1. **Initialize from entry_point**

a. Call `get_function_snippet(entry_point.file_id, entry_point.name)` to extract calls within the entry function.
b. For each `expr` returned:

* Use `get_deps_by_file_id_and_expr(entry_point.file_id, expr)` to find candidate target file_ids.
* If multiple IDs are returned:

  * Compare `expr` against each candidate's `path` to determine the correct target.
  * If still ambiguous, call `get_file_content(candidate_id)` to confirm.
    c. Append confirmed calls as **new nodes** to the `call_chain`.

---

### 2. **Iterative Discovery (Query Until Empty)**

* Maintain a queue of nodes to process.
* While the queue is **not empty**:

  1. Pop the next node (`file_id`, `method`).
  2. Run `get_function_snippet(file_id, method)` to extract its calls.
  3. For each call:

     * Resolve with `get_deps_by_file_id_and_expr(file_id, expr)`.
     * Disambiguate (path check → `get_file_content` if needed).
     * Add confirmed new nodes to both the call_chain and the queue.
* Stop **only when no new calls are discovered** (queue empty).

---

### 3. **Edge Cases**

* **Self-recursion (`this.xxx` or same file_id)**: Skip to avoid infinite loops.
* **Interfaces**:

  * If a candidate is an interface:

    * Use `get_deps_to(interface_file_id)` to find implementers.
    * Validate implementer via `get_function_snippet` or `get_file_content` before adding to the chain.
* ** 沒有查詢結果也要回應空結構並在 `stop_reason` 說明原因** (e.g., no calls found, all calls self-recursive, etc.)
---
## DRAFT OUTPUT (must-do)
- When the queue becomes empty (no new calls found), emit exactly ONE TextMessage.
- It MUST start with exactly: DRAFT:
- Immediately follow with ONE block delimited by <DRAFT> ... </DRAFT>, using these tags:

  <DRAFT>
    <ENTRY file_id="<int>" name="<entry_function_name>" />
    <NODES>
      <NODE file_id="<int>" method="<name>" reason="<short why>" />
      <!-- repeat <NODE ... /> for each discovered node -->
    </NODES>
    <STOP_REASON><short reason why traversal stopped></STOP_REASON>
  </DRAFT>

- Do NOT call tools after emitting the DRAFT.
- Do NOT output the final schema; only the DRAFT block above.
- Keep the tags on a single line per element (no extra attributes).
""")
    
    async def analyze_call_chain(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze function call chain based on the provided prompt
        
        Args:
            prompt: JSON string containing entry_point information
            
        Returns:
            Dictionary containing the call chain analysis result
        """
        try:
            # Initialize clients and tools if not already done
            await self._initialize()
            
            # Parse the prompt to extract entry point information
            task_input = json.loads(prompt)
            entry_point = EntryPoint(**task_input["entry_point"])
            
            # Create agents
            analyzer = self._create_analyzer_agent(entry_point.name)
            finisher = self._create_finisher_agent(entry_point.name)
            
            # Set up the team
            custom_types = [StructuredMessage[CallChainResult]]
            team = RoundRobinGroupChat(
                [analyzer, finisher], 
                termination_condition=SourceMatchTermination(sources=[f"{entry_point.name}_call_chain_finisher"]),
                custom_message_types=custom_types
            )
            
            # Run the analysis
            result = await Console(team.run_stream(task=prompt), output_stats=True)
            
            if not result.messages:
                return {"error": "No response messages"}
            
            last_message = result.messages[-1]
            
            if isinstance(last_message, StructuredMessage) and hasattr(last_message.content, "model_dump"):
                return last_message.content.model_dump()
            elif isinstance(last_message, TextMessage):
                return {"error": "Finisher returned TextMessage", "content": last_message.content}
            else:
                return {"error": f"Unexpected last message type: {type(last_message).__name__}"}
                
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON prompt: {e}"}
        except Exception as e:
            return {"error": f"Analysis failed: {e}"}