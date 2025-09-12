from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from src.agent.function_tool.dependency_tools import create_dependency_tools
from src.agent.function_tool.source_code_tools import create_source_code_tools
from src.core.config import Config

class CallChainAnalyzerAgent:
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
                function_calling=True,
                json_output=True,
                family=None,
                structured_output=False
            ),
            parallel_tool_calls=False,
        )
        
    
    async def get_agent(self, func_name: str) -> AssistantAgent:
        if not func_name:
            raise ValueError("Function name is required to create CallChainAnalyzerAgent")
        
        dependency_tools = await create_dependency_tools(self.run_id)
        source_code_tools = await create_source_code_tools(self.run_id)
        
        tools = [
            dependency_tools["get_func_map"],
            dependency_tools["find_caller_by_dep"],
            source_code_tools["get_file_content"]
        ]
        
        return AssistantAgent(
            name=f"{func_name[:50]}_anlz",
            model_client=self._get_client(),
            tools=tools,
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

## WORKFLOW (follow exactly)

### 1. **Initialize from entry_point**

a. Call `get_func_map(entry_point.file_id, entry_point.component, entry_point.name)` to extract calls within the entry function.
b. For each `expr` in the calls returned:

* Use `find_caller_by_dep(entry_point.file_id, entry_point.component, expr)` to find possible dependency components.
* The tool returns possible dependency component information (file_id, type, component, method).
* For each potential dependency component, use the `expr` to determine if it matches the call pattern.
* Use `get_func_map(file_id, component, method)` to query the corresponding dependencies of confirmed matches.
* Add confirmed calls as **new nodes** to the `call_chain`.

---

### 2. **Iterative Discovery (Query Until Empty)**

* Maintain a queue of nodes to process.
* While the queue is **not empty**:

  1. Pop the next node (`file_id`, `component`, `method`).
  2. Run `get_func_map(file_id, component, method)` to extract its internal calls.
  3. For each call expression:

     * Use `find_caller_by_dep(file_id, component, expr)` to get possible dependency components.
     * For each potential dependency, use the `expr` to determine call chain targets.
     * Use `get_func_map()` on confirmed targets to query their dependencies.
     * Add confirmed new nodes to both the call_chain and the queue.
* Stop **ONLY when the queue is empty AND no new calls are discovered should the process stop**.
* Inspect Before terminating, review the last tool call. If find_caller_by_dep returned any valid dependencies, ensure that get_func_map has been called on each of them. If not, this indicates a failure to complete the task

---

### 3. **Edge Cases**

* **Self-recursion (`this.xxx` or same file_id)**: Skip to avoid infinite loops.
* **Interfaces**: Skip interfaces (type="interface") since we need actual call chains, not interface definitions.
* **Empty Results**: Always respond with empty structure and explain reason in `stop_reason` (e.g., no calls found, all calls self-recursive, etc.)
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