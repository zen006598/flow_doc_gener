import asyncio
import json
from datetime import datetime
from src.analyzer.code_dependency_analyzer import CodeDependencyAnalyzer
from src.core.config import Config
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from src.model.source_code_manager import SourceCodeManager
from src.model.snapshot_manager import SnapshotManager
from src.service.entry_point_extractor import EntryPointExtractor
from src.service.call_chain_analyzer_service import CallChainAnalyzerService
from src.service.feature_analyzer_service import FeatureAnalyzerService
from src.model.call_chain_models import CallChainResult
from src.utils import remove_empty_arrays, crawl_local_files

EXCLUDE_PATTERNS = {"*.md", "dockerfile", "*test*", "*Test*", "*test*/*", 
                    "*Test*/*", "*/test*/*", "*/Test*/*", "tests/*", 
                    "test/*", "__tests__/*", "Program.cs", "*/Program.cs", "*/Startup.cs","Startup.cs", "migrations/*", "*/migrations/*", "*/Migrations/*", "*/migrations/*", "*/Migrations/*"}
INCLUDE_PATTERNS = {"*.cs"}

async def main():
    conf = Config()
    target_dir = None
    _run_id = "20250823T024146Z"
    appoint_entries = []
    
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
    
    entry_points_data = None
    if appoint_entries:
        entry_points_data = extractor.extract_manually(file_deps, appoint_entries)
    else:
        entry_points_data = await extractor.extract_with_agent(client, file_deps)
        print("sleep 60 seconds to avoid rate limit")
        await asyncio.sleep(60)

    if not entry_points_data or len(entry_points_data.get("entries", [])) == 0:
        print("No entry points extracted.")
        return

    snapshot_manager.save_file(run_id, entry_point_cache_file, entry_points_data)
    extract_count = len(entry_points_data.get("entries", []))
    print(f"extract {extract_count} entry points")
    entries_cache = snapshot_manager.load_file(run_id, entry_point_cache_file)

    call_chain_service = CallChainAnalyzerService(conf, run_id)
    feature_analyzer_service = FeatureAnalyzerService(conf)
    
    for entry in entries_cache.get("entries", []):
        entry_name = entry.get("name")
        component = entry.get("component")
        file_id = entry.get("file_id")
        
        print(f"Analyzing: {component}.{entry_name}")
        
        # Create prompt for the service
        prompt = json.dumps({
            "entry_point": {
                "name": entry_name,
                "component": component,
                "file_id": file_id
            }
        })
        
        # Analyze using the service
        result = await call_chain_service.analyze_call_chain(prompt)
        
        # Handle call chain analysis result with early return
        if not result or "error" in result:
            error_msg = result.get("error", "Unknown error") if result else "No result"
            print(f"Warning：{component}.{entry_name} 沒有產生分析結果: {error_msg}")
            print("sleep 60 seconds to avoid rate limit")
            await asyncio.sleep(60)
            continue

        # Save call chain result to analyze_result directory
        output_filename = f"analyze_result/{component}.{entry_name}.json"
        snapshot_manager.save_file(run_id, output_filename, result)
        
        # Sleep before feature analysis (separate AI service call)
        print("sleep 60 seconds to avoid rate limit")
        await asyncio.sleep(60)
        
        # Perform feature analysis
        print(f"Analyzing feature for: {component}.{entry_name}")
        
        # Extract all file_ids from call chain result using the model method
        call_chain_cache = snapshot_manager.load_file(run_id, output_filename)
        call_chain_result = CallChainResult(**call_chain_cache)
        file_ids = call_chain_result.extract_all_file_ids()
        
        # Load source code for these files using SourceCodeManager
        source_files = source_code_manager.get_source_files_by_ids(run_id, file_ids)
        if not source_files:
            print(f"Warning: No source code found for file_ids: {file_ids}")
            print("sleep 60 seconds to avoid rate limit")
            await asyncio.sleep(60)
            continue
        
        # Analyze feature
        try:
            feature_result = await feature_analyzer_service.analyze_feature(entry_name, source_files)
            
            if feature_result and "error" not in feature_result:
                feature_output_filename = f"feature_result/{component}.{entry_name}.feature.json"
                snapshot_manager.save_file(run_id, feature_output_filename, feature_result)
                print(f"Feature analysis saved: {feature_output_filename}")
            else:
                error_msg = feature_result.get("error", "Unknown error") if feature_result else "No result"
                print(f"Warning: Feature analysis failed for {component}.{entry_name}: {error_msg}")
                
        except Exception as e:
            print(f"Error during feature analysis for {component}.{entry_name}: {e}")
        
        print("sleep 60 seconds to avoid rate limit")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
