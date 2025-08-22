import asyncio
import logging
import json
from datetime import datetime
from src.agent.call_chain_analyzer import call_chain_analyzer
from src.agent.function_tool.dependency_tools import create_dependency_tools
from src.agent.function_tool.source_code_tools import create_source_code_tools
from src.analyzer.code_dependency_analyzer import CodeDependencyAnalyzer
from src.core.config import Config
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_core.models._model_client import ModelInfo
from autogen_agentchat.ui import Console
from src.model.source_code_manager import SourceCodeManager
from src.model.snapshot_manager import SnapshotManager
from src.service.entry_point_extractor import EntryPointExtractor
from src.utils import extract_json_response, remove_empty_arrays, crawl_local_files

# logging.basicConfig(level=logging.WARNING)
# event_logger = logging.getLogger(EVENT_LOGGER_NAME)
# event_logger.addHandler(logging.StreamHandler())
# event_logger.setLevel(logging.DEBUG)

EXCLUDE_PATTERNS = {"*.md", "dockerfile", "*test*", "*Test*", "*test*/*", 
                    "*Test*/*", "*/test*/*", "*/Test*/*", "tests/*", 
                    "test/*", "__tests__/*", "Program.cs", "*/Program.cs", "*/Startup.cs","Startup.cs", "migrations/*", "*/migrations/*", "*/Migrations/*", "*/migrations/*", "*/Migrations/*"}
INCLUDE_PATTERNS = {"*.cs"}

async def main():
    conf = Config()
    target_dir = "C:\\Users\\h3098\\Desktop\\Repos\\HousePrice.WebService.Community\\HousePrice.Webservice.Community"
    _run_id = "20250821T165442Z"
    appoint_entries = ["GetCompanyBasicListByAddressAsync", "GetLitigationListAsync"]
    
    source_code_cache_file = conf.cache_file_name_map["source_code"]
    dependence_cache_file = conf.cache_file_name_map["dependence"]
    entry_point_cache_file = conf.cache_file_name_map["entry_point"]
    
    snapshot_manager = SnapshotManager(conf.cache_path)
    source_code_manager = SourceCodeManager(snapshot_manager, file_name=source_code_cache_file)
    
    # Determine run_id: if specified and exists in cache, use it; otherwise generate new one
    if _run_id and source_code_manager.is_snapshot_exists(_run_id):
        run_id = _run_id
        print(f"Using existing snapshot: {run_id}")
    else:
        run_id = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        print(f"Creating new snapshot: {run_id}")
        files = crawl_local_files(directory=target_dir,exclude_patterns=EXCLUDE_PATTERNS, include_patterns=INCLUDE_PATTERNS, use_relative_paths=True)
        source_code_manager.save_snapshot(files, run_id)

    # check cache first
    if snapshot_manager.file_exists(run_id, dependence_cache_file):
        print(f"Loading existing analysis results for {run_id}")
        file_deps = snapshot_manager.load_file(run_id, dependence_cache_file)
    else:
        print(f"Analyzing project dependencies for {run_id}")
        analyzer = CodeDependencyAnalyzer(snapshot_manager)
        file_deps = analyzer.analyze_project(run_id, source_code_cache_file)
        filtered_deps = remove_empty_arrays(file_deps)
        
        snapshot_manager.save_file(run_id, dependence_cache_file, filtered_deps)
    
    extractor = EntryPointExtractor(snapshot_manager)
    
    client = OpenAIChatCompletionClient(
        model=conf.default_model,
        api_key=conf.api_key_map["gemini"],
        base_url=conf.base_url_map["gemini"],
        model_info=ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family=None,
            structured_output=False
        ),
        parallel_tool_calls=False,
    )
    
    dependency_tools = await create_dependency_tools(snapshot_manager, run_id)
    source_code_tools = await create_source_code_tools(snapshot_manager, run_id)
    
    extract_count = 0
    if appoint_entries:
        extract_count = extractor.extract_manually(file_deps, appoint_entries, run_id, entry_point_cache_file)
    else:
        
        extract_count = await extractor.extract_with_agent(
            client, file_deps, run_id, entry_point_cache_file
        )
        
    if extract_count == 0:
        print("No entry points extracted.")
        return

    print(f"extract {extract_count} entry points")
    analyzed_count = 1
    entries_cache = snapshot_manager.load_file(run_id, entry_point_cache_file)
    
    for entry in entries_cache.get("entries", []):
        entry_name = entry.get("name")
        component = entry.get("component") 
        file_id = entry.get("file_id")
        
        print(f"({analyzed_count}/{extract_count})Analyzing: {component}.{entry_name}")
        
        call_chain_agent = await call_chain_analyzer(
            agent_name=f"{entry_name}_call_chain_analyzer",
            client=client, 
            agent_tools=[
                dependency_tools["get_function_snippet"],
                dependency_tools["get_deps_by_file_id_and_expr"],
                dependency_tools["get_deps_to"],
                source_code_tools["get_file_content"]
            ]
        )
        
        task_input = {
            "entry_point": {
                "name": entry_name,
                "component": component,
                "file_id": file_id
            }
        }
        
        analyzed_result = await Console(
            call_chain_agent.run_stream(task=json.dumps(task_input)),
            output_stats=True)
    
        if analyzed_result.messages and analyzed_result.messages[-1] and analyzed_result.messages[-1].content:
            content = analyzed_result.messages[-1].content
            json_content = extract_json_response(content) 
            output_filename = f"{component}.{entry_name}.json"
            snapshot_manager.save_file(run_id, output_filename, json.loads(json_content))

        else:
            print(f"Warning：{component}.{entry_name} 沒有產生分析結果")
        analyzed_count += 1


if __name__ == "__main__":
    asyncio.run(main())
