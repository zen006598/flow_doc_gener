import asyncio
import re
from datetime import datetime
from typing import Optional
from openai import RateLimitError

from src.agent import CallChainAnalyzerAgent, CallChainFinisherAgent, EntryPointDetectorAgent, FeatureAnalyzerAgent, GenerateChartAgent, GenerateDocumentationAgent
from src.analyzer.code_dependency_analyzer import CodeDependencyAnalyzer
from src.analyzer.language_analyze_provider import LanguageAnalyzeProvider
from src.core.config import Config
from src.entity import FeatureStatusEntity
from src.model import CallChainAnalysisModel, DependencyModel, EntryPointModel, FeatureAnalysisModel, FuncMapModel, SourceCodeModel, FeatureStatusModel, ChartModel
from src.service import AnalysisService,DependencyService,EntryPointService, SourceCodeService, FuncMapService, ChartService, GenerateDocumentationService
class Pipeline:
    def __init__(self, config: Config):
        self.config = config
    
    async def run(
        self, 
        target_dir: str, 
        lang: str = '中文',
        run_id: Optional[str] = None,
        appoint_entries: Optional[list[str]] = None
    ):
        # Generate or use provided run_id
        if not run_id:
            run_id = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        
        print(f"Starting pipeline with run_id: {run_id}")
        
        source_code_model = SourceCodeModel(run_id)
        dependency_model = DependencyModel(run_id)
        func_map_model = FuncMapModel(run_id)
        entry_point_model = EntryPointModel(run_id)
        call_chain_analysis_model = CallChainAnalysisModel(run_id)
        feature_analysis_model = FeatureAnalysisModel(run_id)
        feature_status_model = FeatureStatusModel(run_id)
        chart_model = ChartModel(run_id)
        lang_provider = LanguageAnalyzeProvider()
        code_analyzer = CodeDependencyAnalyzer()
        
        entry_point_detector_agent =  EntryPointDetectorAgent(self.config)
        
        source_code_service = SourceCodeService(self.config, source_code_model)
        func_map_service = FuncMapService(
            func_map_model, source_code_model, lang_provider
        )
        dependency_service = DependencyService(
            dependency_model, func_map_model, code_analyzer
        )
        entry_point_service = EntryPointService(self.config, 
            entry_point_model, func_map_model,
            source_code_model, entry_point_detector_agent
        )
        call_chain_analyzer_agent = CallChainAnalyzerAgent(self.config, run_id)
        call_chain_finish_agent = CallChainFinisherAgent(self.config)
        feature_analyzer_agent = FeatureAnalyzerAgent(self.config, lang)
        
        analysis_service = AnalysisService(
            entry_point_model,
            call_chain_analysis_model,
            feature_analysis_model,
            source_code_model,
            call_chain_analyzer_agent,
            call_chain_finish_agent,
            feature_analyzer_agent
        )
        
        generate_chart_agent = GenerateChartAgent(self.config, lang)
        chart_service = ChartService(chart_model, feature_analysis_model, generate_chart_agent)
        
        generate_documentation_agent = GenerateDocumentationAgent(self.config, lang)
        documentation_service = GenerateDocumentationService(
            run_id, feature_analysis_model, chart_model, generate_documentation_agent)
        
        # Step 1: Source code extraction
        if not source_code_service.has_cache():
            source_code_ent = source_code_service.crawl_repo(target_dir)
            print(f"--- Crawled {len(source_code_ent)} files ---")
            source_code_service.save_cache(source_code_ent)
        
        # Step 2: Function mapping and dependency analysis
        if not func_map_service.has_cache():
            print(f"--- Analyzing functions ---")
            func_map = func_map_service.analyze_file()
            func_map_service.save_cache(func_map)
            
        if not dependency_service.has_cache():
            print(f"--- Analyzing dependencies ---")
            deps = dependency_service.analyze_dependencies()
            dependency_service.save_cache(deps)
            
        # Step 3: Entry point extraction
        if not entry_point_service.has_cache():
            print(f"--- Analyzing entry points ---")
            entry_points = await entry_point_service.extract_entry_points(appoint_entries)
            
            if not entry_points:
                print(f"Error: No entry points found for run_id {run_id}")
                return
            
            entry_point_service.save_cache(entry_points)

        # Reset feature status for all entry points
        feature_status_model.truncate()
        feature_statuses = [
            FeatureStatusEntity(
                id=ep.entry_id,
                component=ep.component,
                name=ep.name,
                state="pending",
                retry_count=0
            )
            for ep in entry_point_model.all()
        ]
        feature_status_model.batch_insert(feature_statuses)
        
        # Step 4: Analysis feature - 重複執行直到全部完成
        retry_max_time = 3
        while feature_status_model.has_pending_work(retry_max_time):
            pending_entries = feature_status_model.get_pending_or_failed_entries(retry_max_time)
            
            for status_entry in pending_entries:
                # 從 entry_point_model 找到對應的完整 entry point 資訊
                ep = next((ep for ep in entry_point_model.all() if ep.entry_id == status_entry.id), None)
                if not ep:
                    continue

                print(f"--- Analyzing {ep.component}.{ep.name} (attempt {status_entry.retry_count + 1}) ---")
                
                try:
                    feature_status_model.to_running(ep.entry_id)
                    
                    # Call chain analysis
                    if not analysis_service.has_analyze_call_chain_cache(ep):
                        await analysis_service.analyze_call_chain(ep)
                    else:
                        print(f" > HIT CACHE: Call chain analysis for {ep.component}.{ep.name}")
                        
                    # Feature analysis
                    if not analysis_service.has_analyze_feature_cache(ep):
                        await analysis_service.analyze_feature(ep)
                    else:
                        print(f" > HIT CACHE: Feature analysis for {ep.component}.{ep.name}")
                        
                    # generate chart 
                    if not chart_service.has_cache(ep.entry_id):
                        chart = await chart_service.generate_chart(ep)
                        chart_service.save_cache(chart)
                    else:
                        print(f" > HIT CACHE: Chart for {ep.component}.{ep.name}")
                        
                    # generate documentation
                    if not documentation_service.has_cache(ep):
                        await documentation_service.generate_and_save(ep)
                    else:
                        print(f" > HIT CACHE: Documentation for {ep.component}.{ep.name}")
                        
                    feature_status_model.to_done(ep.entry_id)
                    print(f"Completed {ep.component}.{ep.name}")

                except (RateLimitError, Exception) as e:
                    # Check if it's a rate limit error (could be wrapped)
                    if "429" in str(e) or "rate limit" in str(e).lower() or "quota" in str(e).lower():
                        delay = self._parse_retry_delay_seconds(e)
                        if delay is not None:
                            delay += 5
                            print(f" > Rate limit exceeded, will retry after {delay} seconds")
                            await asyncio.sleep(delay)
                        else:
                            print(f" > Rate limit exceeded, will retry after 60 seconds")
                            await asyncio.sleep(60)
                        feature_status_model.inc_retry(ep.entry_id)
                        feature_status_model.to_failed(ep.entry_id)  # Mark as failed to be picked up in next iteration
                    else:
                        # Other exceptions - increment retry and mark as failed
                        feature_status_model.inc_retry(ep.entry_id)
                        feature_status_model.to_failed(ep.entry_id)
                        print(f"{ep.component}.{ep.name} failed with error: {str(e)}")
            
            # Small delay between iterations to avoid tight loop
            if feature_status_model.has_pending_work(retry_max_time):
                await asyncio.sleep(1)

            
    def _parse_retry_delay_seconds(self, e: Exception) -> Optional[int]:
        """從 Gemini/Google 風格錯誤物件中抓 retryDelay（形如 '36s'）"""
        s = str(e)
        match = re.search(r'"retryDelay":\s*"(\d+)s"', s)
        if match:
            return int(match.group(1))
        return None
        