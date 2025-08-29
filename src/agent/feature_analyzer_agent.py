from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models._model_client import ModelInfo
from src.core.config import Config
from src.entity import FeatureAnalysisEntity

class FeatureAnalyzerAgent:
    def __init__(self, config: Config, lang: str):
        self.config = config
        self.lang = lang
        
    def _get_client(self) -> ChatCompletionClient:
        return OpenAIChatCompletionClient(
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
            max_retries=3
        )
    
    def get_agent(self, func_name: str) -> AssistantAgent:
        if not func_name:
            raise ValueError("Function name is required to create CallChainAnalyzerAgent")
        
        return AssistantAgent(
            name=f"{func_name}_feature_analyzer",
            model_client=self._get_client(),
            output_content_type=FeatureAnalysisEntity,
            system_message=f"""You are a **Feature Analysis Agent**. Your task is to analyze the complete functionality of an entry point by examining all related source code files and producing a {self.lang} comprehensive feature analysis.

## Input Format
You will receive a JSON object containing function name and source code files:
```json
{{
    "func": "<function_name>",
    "contents": [
        {{
            "file_id": <int>,
            "path": "<string>",
            "content": "<source code>"
        }},
        ...
    ]
}}
```

## Analysis Requirements

Analyze the target function specified in the "func" field and all related code to extract:

### 1. Basic Information
- **entry_point_name**: Use the function name from the "func" field as the main function/method name
- **http_url**: Extract HTTP route/endpoint if this is a web API (e.g., "/api/clients/{{id}}")
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