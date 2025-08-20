import asyncio
import logging
import json
from datetime import datetime
from src.core.config import Config
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from autogen_core.models._model_client import ModelInfo
from autogen_agentchat.ui import Console
from src.entity.entry_point import EntryPoint
from src.entity.entry_point_response import EntryPointResponse
from src.model.file_snapshot import FileSnapshot
from src.utils.crawl_local_files import crawl_local_files

logging.basicConfig(level=logging.WARNING)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
trace_logger.addHandler(logging.StreamHandler())
trace_logger.setLevel(logging.DEBUG)

event_logger = logging.getLogger(EVENT_LOGGER_NAME)
event_logger.addHandler(logging.StreamHandler())
event_logger.setLevel(logging.DEBUG)

EXCLUDE_PATTERNS = {"*.md", "dockerfile", "*test*", "*Test*", "*test*/*", 
                    "*Test*/*", "*/test*/*", "*/Test*/*", "tests/*", 
                    "test/*", "__tests__/*"}
INCLUDE_PATTERNS = {"*.cs"}

async def main():
    conf = Config()
    target_dir = "C:\\Users\\h3098\\Desktop\\Repos\\HousePrice.WebService.Community"
    _run_id = "20250820T095222Z"
    run_id = _run_id or datetime.now().strftime("%Y%m%dT%H%M%SZ")
    file_snapshot = FileSnapshot(run_id=run_id)

    # Check if snapshot already exists, skip if it does
    if file_snapshot.snapshot_exists():
        print(f"{run_id} already exists, use snapshot.")
    else:
        files = crawl_local_files(directory=target_dir,exclude_patterns=EXCLUDE_PATTERNS, include_patterns=INCLUDE_PATTERNS, use_relative_paths=True)
        file_snapshot.save_snapshot(files)

    appoint_entries = ["GetCompanyBasicListByAddressAsync", "GetNotSendMailDataAsync"]
    with open("data/community.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    client = OpenAIChatCompletionClient(
            model=conf.default_model,
            api_key=conf.api_key_map["gemini"],
            base_url=conf.base_url_map["gemini"],
            model_info=ModelInfo(
                vision=False,
                function_calling=True,
                json_output=True,
                family=None,
                structured_output=True
            ),
            parallel_tool_calls=False,
        )
    
    detector_agent = AssistantAgent(
        "entry_point_detector",
        model_client=client,
        output_content_type=EntryPointResponse,
        system_message=(
            """<role>You are a senior software architect focused EXCLUSIVELY on discovering API/feature ENTRY POINTS from a static dependency map. You DO NOT expand call chains.</role>
<task>From the given dependency analysis (schema below), identify all likely entry points (API endpoints or functional entry points).</task>
<input.schema>
The analysis_result JSON has two top-level parts:

1) files: per-file symbol info
{{
  "files": {{
    "<file_id>": {{
      "path": "file path",
      "funcs": ["function names"],
      "cls": ["class names"],
      "calls": ["outgoing call names (simplified)"],
      "fcalls": {{ "<func>": [ {{ "method": "<callee>", "expr": "<call expression>" }} ] }}
    }}
  }}
}}

2) deps: function-level edges
[
  {{
    "from": "<file_id>",
    "from_func": "<caller>",
    "to": "<file_id>",
    "to_func": "<callee>",
    "call": {{"method": "<callee>", "expr": "<call expr>"}}
  }}
]
</input.schema>

<entrypoint.definition>
Treat a function as an ENTRY POINT if ANY of the following heuristics match:

A. HTTP Controllers (ASP.NET / MVC)
  • file.path contains "/Controllers/" or "\\Controllers\\", OR any class name endsWith "Controller"
  • All listed funcs in that file are candidate controller actions (assume public unless told otherwise)

B. Minimal API (Program.cs / Startup)
  • file.calls contains any of: MapGet, MapPost, MapPut, MapDelete, MapPatch, MapGroup, MapControllerRoute
  • Record an entry for each Map* occurrence; if funcs are absent, set name to the Map* method (e.g., "MapGet") and component "Program"

C. Background Jobs / Schedulers
  • class names or file.path hint "Job", "Quartz", "Hangfire", "Worker", "HostedService", "BackgroundService"
  • functions like Execute/ExecuteAsync/Run are entries

D. Event/Queue Consumers
  • class names with "Handler", "Consumer", "Subscriber", "Listener", "Receiver"
  • functions like Handle/Consume/OnMessage/Process are entries

E. CLI / Batch
  • funcs include "Main" or file.path suggests console tool; mark "Main" as entry

F. RPC / gRPC / GraphQL (best-effort)
  • presence of cls ending with "Service" paired with framework signals in calls (e.g., AddGrpc, MapGrpcService) ⇒ funcs are entries of type "grpc_service"
  • classes named "Query" or "Mutation" ⇒ funcs are entries of type "graphql_resolver"

G. Cross-check with deps (supporting signal)
  • If a method appears as a caller (deps.from_func) and its file meets any heuristic above, boost confidence.

Notes:
- If visibility/attributes are unavailable, prefer recall (include rather than exclude) but score confidence accordingly.
- Dedupe by (path, component, name).
- Mark missing component with "[unknown]".
</entrypoint.definition>

<procedure>
0) Filter (if <entry_filter> provided):
   - Build a candidate set of names from <entry_filter>.names using the selected match rule.
   - Only consider functions whose names match this set.
1) Scan files.* and apply heuristics A–F to the considered functions/classes.
2) Use deps[] only to increase confidence for callers found in step 1.
3) Dedupe and sort:
   - Order: http_controller_action → minimal_api → job → event_consumer → grpc_service → graphql_resolver → cli → other
4) Emit JSON strictly.
</procedure>

<constraints>
- Do NOT invent routes/HTTP verbs if absent.
- Be conservative with confidence when only weak signals exist.
- Output may be an empty "entries": [] when filtering yields no matches.
- Output must be valid JSON and nothing else.
</constraints>

<example.small>
Given:
files["2"].path = "...\\Controllers\\AdCase\\AdCaseController.cs"
files["2"].funcs = ["SearchByAdTypeAsync","SearchByAdTypeByMrtAsync"]
Case A (no <entry_filter>): produce two http_controller_action entries with high confidence and reasons:["class endsWith Controller","path contains Controllers"].
Case B (<entry_filter> = "SearchByAdTypeAsync"): produce ONLY the "SearchByAdTypeAsync" entry. If not found, "entries": [].
</example.small>"""),
    )
    
    detect_prompt = {
        "files": data["files"],
        "deps": data["deps"]
    }
    
    if appoint_entries:
        detect_prompt["entry_filter"] = appoint_entries
            
    detector_response = await Console(detector_agent.run_stream(task=json.dumps(detect_prompt)))
    last_detector_response = detector_response.messages[-1].content
    
    if isinstance(last_detector_response, EntryPointResponse):
        entries = last_detector_response.entries
    elif isinstance(last_detector_response, str):
        try:
            response_data = json.loads(last_detector_response)
            entries_data = response_data.get("entries", [])
            entries = [EntryPoint(**entry) for entry in entries_data]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"解析 detector 回應時發生錯誤: {e}")
            entries = []
    else:
        entries = []
        
    if not entries:
        print("沒有找到入口點")
        return []
            
    entries = [entry.model_dump() for entry in entries]
    detector_output_file = "data/entry_points.json"
    with open(detector_output_file, "w", encoding="utf-8") as f:
        json.dump({
            "entry_filter": appoint_entries,
            "entries": entries
        }, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
