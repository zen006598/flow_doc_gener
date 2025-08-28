from datetime import datetime
from typing import Optional

from src.agent.call_chain_analyzer_agent import CallChainAnalyzerAgent
from src.agent.call_chain_finisher_agent import CallChainFinisherAgent
from src.agent.entry_point_detect_agent import EntryPointDetectorAgent
from src.agent.feature_analyzer_agent import FeatureAnalyzerAgent
from src.analyzer.code_dependency_analyzer import CodeDependencyAnalyzer
from src.analyzer.language_analyze_provider import LanguageAnalyzeProvider
from src.core.config import Config
from src.model import DependencyModel, EntryPointModel, FuncMapModel, SourceCodeModel, CallChainAnalysisModel, FeatureAnalysisModel
from src.service import AnalysisService, SourceCodeService, DependencyService, EntryPointService

class Pipeline:
    def __init__(self, config: Config):
        self.config = config
    
    async def run_pipeline(
        self, 
        target_dir: str, 
        run_id: Optional[str] = None,
        appoint_entries: Optional[list[str]] = None
    ):
        # Generate or use provided run_id
        if not run_id:
            run_id = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        
        print(f"Starting pipeline with run_id: {run_id}")
        
        # Initialize services with models
        source_code_model = SourceCodeModel(run_id)
        dependency_model = DependencyModel(run_id)
        file_function_map_model = FuncMapModel(run_id)
        entry_point_model = EntryPointModel(run_id)
        call_chain_analysis_model = CallChainAnalysisModel(run_id)
        feature_analysis_model = FeatureAnalysisModel(run_id)
        
        lang_provider = LanguageAnalyzeProvider()
        code_analyzer = CodeDependencyAnalyzer()
        
        entry_point_detector_agent =  EntryPointDetectorAgent(self.config)
        
        source_code_service = SourceCodeService(self.config, source_code_model)
        dependency_service = DependencyService(
            dependency_model, file_function_map_model,
            source_code_model, code_analyzer, lang_provider
        )
        
        entry_point_service = EntryPointService(self.config, 
            entry_point_model, file_function_map_model,
            source_code_model, entry_point_detector_agent
        )
        call_chain_analyzer_agent = CallChainAnalyzerAgent(self.config, run_id)
        call_chain_finish_agent = CallChainFinisherAgent(self.config)
        feature_analyzer_agent = FeatureAnalyzerAgent(self.config)
        
        analysis_service = AnalysisService(
            entry_point_model,
            call_chain_analysis_model,
            feature_analysis_model,
            source_code_model,
            call_chain_analyzer_agent,
            call_chain_finish_agent,
            feature_analyzer_agent
        )
        
        # Step 1: Source code extraction
        if not await source_code_service.ensure_source_code(target_dir):
            print(f"Error: Failed to extract source code for run_id {run_id}")
            return
        
        # Step 2: Dependency analysis
        if not await dependency_service.ensure_dependencies():
            print(f"Error: Failed to analyze dependencies for run_id {run_id}")
            return
        
        # Step 3: Entry point extraction
        if not await entry_point_service.ensure_entry_points(appoint_entries):
            print(f"Error: Failed to extract entry points for run_id {run_id}")
            return
        
        # Step 4: Analysis execution
        if not await analysis_service.run_analysis():
            print(f"Error: Failed to complete analysis for run_id {run_id}")
            return
        
        print(f"Pipeline completed successfully for run_id: {run_id}")