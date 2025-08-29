import json
from pathlib import Path

from src.agent import GenerateDocumentationAgent
from src.entity import EntryPointEntity
from src.model import FeatureAnalysisModel, ChartModel
from autogen_agentchat.ui import Console


class GenerateDocumentationService:
    def __init__(self, 
            run_id: str,
            feature_analysis_model: FeatureAnalysisModel,
            chart_model: ChartModel,
            generate_documentation_agent: GenerateDocumentationAgent):
        self.run_id = run_id
        self.feature_analysis_model = feature_analysis_model
        self.chart_model = chart_model
        self.generate_documentation_agent = generate_documentation_agent
        self.output_dir = Path(f"output/{run_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def has_cache(self, entry_point: EntryPointEntity) -> bool:
        """Check if documentation already exists for this entry point"""
        doc_file = self.output_dir / f"{entry_point.component}.{entry_point.name}.md"
        return doc_file.exists()

    async def generate_documentation(self, entry_point: EntryPointEntity) -> str:
        """Generate documentation for a specific entry point"""
        # Get feature analysis data
        feature_analysis = self.feature_analysis_model.get_by_component_and_entry(
            entry_point.component, entry_point.name)
        if not feature_analysis:
            raise ValueError(f"No feature analysis found for {entry_point.component}.{entry_point.name}")
        
        # Get chart data
        chart_entity = self.chart_model.get(entry_point.entry_id)
        mermaid_chart = chart_entity.mermaid_flow_chart if chart_entity else None
        
        # Prepare prompt combining feature analysis and chart
        prompt_data = {
            "feature_analysis": feature_analysis.model_dump(exclude_none=True),
            "mermaid_flow_chart": mermaid_chart
        }
        
        # Generate documentation using agent
        agent = await self.generate_documentation_agent.get_agent(
            entry_point.component, entry_point.name)
        prompt_str = json.dumps(prompt_data, ensure_ascii=False)
        
        res = await Console(agent.run_stream(task=prompt_str), output_stats=True)
        documentation_content = res.messages[-1].content
        
        return documentation_content

    def save_documentation(self, entry_point: EntryPointEntity, content: str) -> str:
        """Save documentation to output directory"""
        doc_file = self.output_dir / f"{entry_point.component}.{entry_point.name}.md"
        
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Documentation saved: {doc_file}")
        return str(doc_file)

    async def generate_and_save(self, entry_point: EntryPointEntity) -> str:
        """Generate and save documentation in one step"""
        content = await self.generate_documentation(entry_point)
        return self.save_documentation(entry_point, content)

    def get_output_path(self, entry_point: EntryPointEntity) -> str:
        """Get the output path for a specific entry point"""
        return str(self.output_dir / f"{entry_point.component}.{entry_point.name}.md")