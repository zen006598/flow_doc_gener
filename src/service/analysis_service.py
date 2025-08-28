import json

from src.agent.call_chain_analyzer_agent import CallChainAnalyzerAgent
from src.agent.call_chain_finisher_agent import CallChainFinisherAgent
from src.agent.feature_analyzer_agent import FeatureAnalyzerAgent
from src.entity.feature_analysis_entity import FeatureAnalysisEntity
from src.model import EntryPointModel, CallChainAnalysisModel, FeatureAnalysisModel, SourceCodeModel
from src.entity import CallChainResultEntity, EntryPointEntity
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.ui import Console

class AnalysisService:
    def __init__(self, 
            entry_point_model: EntryPointModel,
            call_chain_analysis_model: CallChainAnalysisModel,
            feature_analysis_model: FeatureAnalysisModel,
            source_code_model: SourceCodeModel,
            call_chain_analyzer_agent: CallChainAnalyzerAgent, 
            call_chain_finish_agent: CallChainFinisherAgent,
            feature_analyzer_agent: FeatureAnalyzerAgent):
        
        self.entry_point_model = entry_point_model
        self.call_chain_analysis_model = call_chain_analysis_model
        self.feature_analysis_model = feature_analysis_model
        self.source_code_model = source_code_model
        self.call_chain_analyzer_agent = call_chain_analyzer_agent
        self.call_chain_finish_agent = call_chain_finish_agent
        self.feature_analyzer_agent = feature_analyzer_agent
        
    def _lost_entries_data(self) -> bool:
        return not self.entry_point_model.has_data()
    
    async def run_analysis(self) -> bool:
        if self._lost_entries_data():
            print("Error: No entry points found")
            return False
        
        entries = self.entry_point_model.all()
        
        for entry in entries:
            
            print(f"Analyzing {entry.component}.{entry.name}")
            
            if not self._has_analyze_call_chain_cache(entry):
                await self._analyze_call_chain(entry)
                
            if not self._has_analyze_feature_cache(entry):
                await self._analyze_feature(entry)

        return True
    
    def _has_analyze_call_chain_cache(self, entry_point: EntryPointEntity) -> bool:
        return self.call_chain_analysis_model.find_by_component_and_entry(entry_point.component, entry_point.name)
    
    async def _analyze_call_chain(self, entry_point: EntryPointEntity):           
        prompt = json.dumps({
            "entry_point": {
                "name": entry_point.name,
                "component": entry_point.component,
                "file_id": entry_point.file_id
            }
        })

        analyzer = await self.call_chain_analyzer_agent.get_agent(entry_point.name)
        finisher = self.call_chain_finish_agent.get_agent(entry_point.name)
        
        custom_types = [StructuredMessage[CallChainResultEntity]]
        team = RoundRobinGroupChat(
            [analyzer, finisher], 
            termination_condition=SourceMatchTermination(sources=[f"{entry_point.name}_call_chain_finisher"]),
            custom_message_types=custom_types
        )
        
        result = await Console(team.run_stream(task=prompt), output_stats=True)
        content = result.messages[-1].content
        self.call_chain_analysis_model.insert(content)
        
    def _has_analyze_feature_cache(self, entry_point: EntryPointEntity) -> bool:
        return self.feature_analysis_model.find_by_component_and_entry(entry_point.component, entry_point.name)
    
    async def _analyze_feature(self, entry_point: EntryPointEntity) -> bool:
        call_chain_entity = self.call_chain_analysis_model.find_by_component_and_entry(entry_point.component, entry_point.name)
        if not call_chain_entity:
            print(f"No call chain data found for {entry_point.component}.{entry_point.name}")
            return False
        
        fids = self._extract_file_ids(call_chain_entity)
        source_code_entities = self.source_code_model.find_by_id(fids)
        prompt = json.dumps({
            "func": entry_point.name,
            "contents": [source_file.model_dump() for source_file in source_code_entities]
        })
        
        try:
            
            agent = self.feature_analyzer_agent.get_agent(entry_point.name)
            res = await Console(agent.run_stream(task=prompt), output_stats=True)
            content =  res.messages[-1].content.model_dump()
            self.feature_analysis_model.insert(FeatureAnalysisEntity(**content))

        except Exception as e:
            print(f"Error during feature analysis for {entry_point.component}.{entry_point.name}: {e}")
            return False
        
    def _extract_file_ids(self, call_chain_analyze_result:CallChainResultEntity ) -> list[int]:
        fids = set()
        
        fids.add(call_chain_analyze_result.file_id)
        
        for c in call_chain_analyze_result.call_chain:
            fids.add(c.file_id)
        
        return list(fids)