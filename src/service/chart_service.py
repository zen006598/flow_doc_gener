import json
from src.agent import GenerateChartAgent
from src.entity import ChartEntity, EntryPointEntity
from src.model import ChartModel, FeatureAnalysisModel
from autogen_agentchat.ui import Console


class ChartService:
    def __init__(self, 
            chart_model: ChartModel, 
            feature_analysis_model: FeatureAnalysisModel, 
            generate_chart_agent: GenerateChartAgent):
        self.chart_model = chart_model
        self.feature_analysis_model = feature_analysis_model
        self.generate_chart_agent = generate_chart_agent
        
    def has_cache(self, id: int) -> bool:
        return self.chart_model.is_exist(id)

    async def generate_chart(self, entry_point: EntryPointEntity) -> ChartEntity:
        feat = self.feature_analysis_model.get_by_component_and_entry(entry_point.component, entry_point.name)
        if feat is None:
            raise ValueError(f"No feature analysis found for {entry_point.component}.{entry_point.name}")
        
        agent = await self.generate_chart_agent.get_agent(feat.entry_func_name, feat.entry_component_name)
        # Convert dict to JSON string for agent
        prompt = json.dumps(feat.model_dump(exclude_none=True))
        res = await Console(agent.run_stream(task=prompt), output_stats=True)
        
        # Get the chart data from agent response
        chart_data = res.messages[-1].content
        
        # Create ChartEntity with entry_id
        if isinstance(chart_data, dict):
            chart_data['entry_id'] = entry_point.entry_id
            return ChartEntity(**chart_data)
        else:
            # If chart_data is already a ChartEntity or has model_dump()
            chart_dict = chart_data.model_dump() if hasattr(chart_data, 'model_dump') else chart_data
            chart_dict['entry_id'] = entry_point.entry_id
            return ChartEntity(**chart_dict)

    def save_cache(self, entity: ChartEntity) -> None:
        self.chart_model.insert(entity)