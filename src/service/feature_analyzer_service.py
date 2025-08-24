import json
from typing import List, Dict, Any

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import StructuredMessage, TextMessage

from src.core.config import Config
from src.model.feature_analysis_models import FeatureAnalysis, SourceCodeFile


class FeatureAnalyzerService:
    """Service for analyzing complete feature functionality from source code"""
    
    def __init__(self, config: Config):
        """
        Initialize the service
        
        Args:
            config: Configuration object containing API keys, models, etc.
        """
        self.config = config
        self.client = None
    
    async def _initialize(self):
        """Initialize client asynchronously"""
        if self.client is None:
            self.client = OpenAIChatCompletionClient(
                model=self.config.default_model,
                api_key=self.config.api_key_map["gemini"],
                base_url=self.config.base_url_map["gemini"],
                model_info=ModelInfo(
                    vision=False,
                    function_calling=False,
                    json_output=True,
                    family=None,
                    structured_output=True
                ),
                parallel_tool_calls=False,
            )
    
    def _create_analyzer_agent(self, entry_point_name: str) -> AssistantAgent:
        """Create the feature analyzer agent"""
        return AssistantAgent(
            name=f"{entry_point_name}_feature_analyzer",
            model_client=self.client,
            output_content_type=FeatureAnalysis,
            system_message="""You are a **Feature Analysis Agent** for .NET/C# applications. Your task is to analyze the complete functionality of an entry point by examining all related source code files and producing a comprehensive feature analysis.

## Input Format
You will receive a collection of source code files in this format:
```
file_id: <int>
path: <string>
content: <source code>

file_id: <int>
path: <string>  
content: <source code>
...
```

## Analysis Requirements

Analyze the entry point and all related code to extract:

### 1. Basic Information
- **entry_point_name**: The main function/method name
- **http_url**: Extract HTTP route/endpoint if this is a web API (e.g., "/api/clients/{id}")
- **http_method**: HTTP method (GET, POST, PUT, DELETE, etc.)
- **parameters**: List all function parameters

### 2. Dependencies and Flow
- **include_file_id**: List all file IDs that are involved in this feature
- **call_chains**: Detailed call flow with order, showing how methods call each other

### 3. Data Operations
- **table_read**: Database tables or data sources that are READ
- **table_write**: Database tables or data sources that are WRITTEN/UPDATED/DELETED
- **external_api**: Any external HTTP APIs that are called

### 4. Architecture Analysis
For each step in the call chain, identify:
- **role**: controller, service, repository, domain, infrastructure, or external
- **data_access**: What data is read/written at this step
- **confidence**: How confident you are about this analysis (0.0-1.0)

## Analysis Guidelines

1. **HTTP Endpoints**: Look for attributes like [HttpGet], [HttpPost], [Route], etc.
2. **Database Operations**: Look for Entity Framework, SQL queries, repository patterns
3. **External APIs**: Look for HttpClient calls, REST API calls, third-party service calls  
4. **Call Flow**: Trace the execution from entry point through all method calls
5. **Data Flow**: Track how data flows through the system and what gets persisted

## Output Requirements

Return ONLY structured output matching the FeatureAnalysis schema. Include:
- Accurate HTTP information if it's a web API
- Complete list of involved files
- Detailed call chain with proper ordering
- All data access operations
- External API dependencies
- A comprehensive summary of what this feature does

Focus on accuracy and completeness. If you're unsure about something, indicate it in the confidence score and notes.
""")
    
    async def analyze_feature(self, entry_point_name: str, source_files: List[SourceCodeFile]) -> Dict[str, Any]:
        """
        Analyze feature functionality from source code files
        
        Args:
            entry_point_name: Name of the entry point function
            source_files: List of source code files to analyze
            
        Returns:
            Dictionary containing the feature analysis result
        """
        try:
            # Initialize client if not already done
            await self._initialize()
            
            # Create the analyzer agent
            analyzer = self._create_analyzer_agent(entry_point_name)
            
            # Prepare the prompt with source code files
            prompt_parts = []
            for source_file in source_files:
                prompt_parts.append(f"file_id: {source_file.file_id}")
                prompt_parts.append(f"path: {source_file.path}")
                prompt_parts.append(f"content: {source_file.content}")
                prompt_parts.append("")  # Empty line separator
            
            prompt = "\n".join(prompt_parts)
            
            # Run the analysis
            result = await Console(analyzer.run_stream(task=prompt), output_stats=True)
            
            if not result.messages:
                return {"error": "No response messages"}
            
            last_message = result.messages[-1]
            
            if isinstance(last_message, StructuredMessage) and hasattr(last_message.content, "model_dump"):
                return last_message.content.model_dump()
            elif isinstance(last_message, TextMessage):
                return {"error": "Analyzer returned TextMessage", "content": last_message.content}
            else:
                return {"error": f"Unexpected last message type: {type(last_message).__name__}"}
                
        except Exception as e:
            return {"error": f"Analysis failed: {e}"}