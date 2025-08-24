import asyncio
from datetime import datetime
import json
from typing import Any

from src.analyzer.code_dependency_analyzer import CodeDependencyAnalyzer
from src.core.config import Config
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from src.model.dependency_model import DependencyModel
from src.model.entry_point_model import EntryPointModel
from src.model.feature_analysis_models import SourceCodeFile
from src.model.file_functions_map_model import FileFunctionsMapModel
from src.model.call_chain_model import CallChainAnalysisModel
from src.model.feature_analysis_model import FeatureAnalysisModel
from src.model.source_code_model import SourceCodeModel
from src.service.entry_point_extractor import EntryPointExtractor
from src.service.call_chain_analyzer_service import CallChainAnalyzerService
from src.service.feature_analyzer_service import FeatureAnalyzerService
from src.model.call_chain_models import CallChainResult
from src.utils import remove_empty_arrays
from src.utils.compress_content import compress_content
from src.utils.crawl_local_files import crawl_local_files

EXCLUDE_PATTERNS = {"*.md", "dockerfile", "*test*", "*Test*", "*test*/*", 
                    "*Test*/*", "*/test*/*", "*/Test*/*", "tests/*", 
                    "test/*", "__tests__/*", "Program.cs", "*/Program.cs", "*/Startup.cs","Startup.cs", "migrations/*", "*/migrations/*", "*/Migrations/*", "*/migrations/*", "*/Migrations/*"}
INCLUDE_PATTERNS = {"*.cs"}

async def main():
    conf = Config()
    target_dir = "/Users/chenjungwei/Downloads/TongDeApi"
    _run_id = None
    appoint_entries = ["ItemController.DeleteAsync", "ClientController.GetAsync"]
    
    source_code_cache_file = conf.cache_file_name_map["source_code"]
    
    # Determine run_id and whether to fetch new data
    if _run_id:
        run_id = _run_id
        source_code_model = SourceCodeModel(
            run_id=run_id, table=source_code_cache_file)
        
        if not source_code_model.has_data():
            print(f"Error: No source code data found for run_id {run_id}")
            return
    else:
        run_id = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        source_code_model = SourceCodeModel(run_id)
        
        files = fetch_repo(target_dir=target_dir,
            exclude_patterns=EXCLUDE_PATTERNS,
            include_patterns=INCLUDE_PATTERNS)
        
        source_code_model.batch_insert(files)

    dependency_model = DependencyModel(run_id)
    file_function_map_model = FileFunctionsMapModel(run_id)

    if dependency_model.has_data() and file_function_map_model.has_data():
        print(f"{run_id} | Use cached dependencies")
        file_deps = {
            "files": file_function_map_model.all(),
            "deps": dependency_model.all()
        }
    else:
        print(f"{run_id} | Analyzing dependencies")
        analyzer = CodeDependencyAnalyzer(source_code_model)
        file_deps = analyzer.analyze_project()
        filtered_func_map = remove_empty_arrays(file_deps["files"])
        file_function_map_model.batch_insert(filtered_func_map)
        dependency_model.batch_insert(file_deps["deps"])
    
    entry_point_model = EntryPointModel(run_id)
        
    if not entry_point_model.has_data():
        print(f"{run_id} | Extracting entry points")
        extractor = EntryPointExtractor(file_function_map_model)
        
        entry_points_data = None
        if appoint_entries:
            entry_points_data = extractor.extract_manually(appoint_entries)
            
        if not appoint_entries:
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
            # Convert files list to dict format for extract_with_agent
            files_dict = {str(file_info["file_id"]): file_info for file_info in file_deps["files"]}
            entry_points_data = await extractor.extract_with_agent(client, {"files": files_dict})
            print("sleep 60 seconds to avoid rate limit")
            await asyncio.sleep(60)

        if not entry_points_data:
            print(f"{run_id} | Entry point no found")
            return
        
        entry_point_model.batch_insert(entry_points_data)

    call_chain_service = CallChainAnalyzerService(conf, run_id)
    feature_analyzer_service = FeatureAnalyzerService(conf)
    call_chain_analysis_model = CallChainAnalysisModel(run_id)
    feature_analysis_model = FeatureAnalysisModel(run_id)
    
    for entry in entry_point_model.all():
        entry_name = entry.get("name")
        component = entry.get("component")
        file_id = entry.get("file_id")
        
        print(f"{run_id } | Analyzing {component}.{entry_name}")
        
        prompt = json.dumps({
            "entry_point": {
                "name": entry_name,
                "component": component,
                "file_id": file_id
            }
        })
        
        # Check if call chain analysis already exists
        existing_call_chain = call_chain_analysis_model.find_by_component_and_entry(component, entry_name)
        if existing_call_chain:
            print(f"{run_id} | Use cached call chain: {component}.{entry_name}")
            result = existing_call_chain.get("analysis_data", {})
        else:
            print(f"{run_id} | Analyzing call chain: {component}.{entry_name}")
            # Analyze using the service
            result = await call_chain_service.analyze_call_chain(prompt)
            
            # Handle call chain analysis result with early return
            if not result or "error" in result:
                error_msg = result.get("error", "Unknown error") if result else "No result"
                print(f"{run_id} | Warning: {component}.{entry_name} call chain analysis failed: {error_msg}")
                continue

            # Save call chain result using CallChainAnalysisModel
            call_chain_analysis_model.insert(component, entry_name, result)
            print(f"{run_id} | Call chain analysis saved: {component}.{entry_name}")
        
        print(f"{run_id } | Analyzing feature {component}.{entry_name}")
        
        # Extract all file_ids from call chain result using the model method
        call_chain_cache = call_chain_analysis_model.find_by_component_and_entry(component, entry_name)
        call_chain_result = CallChainResult(**call_chain_cache.get("analysis_data", {}))
        file_ids = call_chain_result.extract_all_file_ids()
        
        source_dicts = source_code_model.list(file_ids)
        source_files = [
            SourceCodeFile(
                file_id=file_dict.get("id"),
                path=file_dict.get("path"),
                content=file_dict.get("content")
            )
            for file_dict in source_dicts
        ]
        
        if not source_files:
            continue
        
        # Check if feature analysis already exists
        existing_feature = feature_analysis_model.find_by_component_and_entry(component, entry_name)
        if existing_feature:
            print(f"{run_id} | Use cached feature analysis: {component}.{entry_name}")
        else:
            print(f"{run_id} | Analyzing feature: {component}.{entry_name}")
            # Analyze feature
            try:
                feature_result = await feature_analyzer_service.analyze_feature(entry_name, source_files)
                
                if feature_result and "error" not in feature_result:
                    feature_analysis_model.insert(component, entry_name, feature_result)
                    print(f"{run_id} | Feature analysis saved: {component}.{entry_name}")
                else:
                    error_msg = feature_result.get("error", "Unknown error") if feature_result else "No result"
                    print(f"{run_id} | Warning: Feature analysis failed for {component}.{entry_name}: {error_msg}")
                    
            except Exception as e:
                print(f"{run_id} | Error during feature analysis for {component}.{entry_name}: {e}")
        
def fetch_repo(
    target_dir:str, 
    exclude_patterns:set[str], 
    include_patterns: set[str]) -> list[dict[str, Any]]:
    files = crawl_local_files(
        directory=target_dir,
        exclude_patterns=exclude_patterns or set(),
        include_patterns=include_patterns or set(),
        use_relative_paths=True
    )
    
    return [
        {
            "id": file.file_id,
            "path": file.path,
            "content": compress_content(file.content)
        }
        for file in files
    ]

if __name__ == "__main__":
    asyncio.run(main())
