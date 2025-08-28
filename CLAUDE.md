# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a flow documentation generator that analyzes C# codebases to automatically generate comprehensive documentation about code flow, dependencies, and feature analysis. The system uses AI agents powered by autogen to perform static code analysis and generates structured documentation about how code components interact.

## Development Commands

```bash
# Run the main analysis pipeline
uv run main.py

# Install dependencies
uv sync

# The project uses UV for dependency management (see pyproject.toml)
```

## Core Architecture

### Data Flow Pipeline
The system processes codebases through several sequential stages:

1. **Source Code Crawling** - Extracts and compresses source code files
2. **Dependency Analysis** - Analyzes code structure, functions, classes, and call relationships 
3. **Entry Point Detection** - Identifies API endpoints, controllers, background jobs, and other entry points
4. **Call Chain Analysis** - Uses AI to trace execution paths from entry points
5. **Feature Analysis** - Generates comprehensive feature documentation using AI

### Storage Architecture (TinyDB-based)
All analysis results are stored in structured TinyDB databases under `cache/{run_id}/`:

- **SourceCodeModel** (`src.json`) - Original source code with compression
- **DependencyModel** (`dep.json`) - Function-level dependency relationships
- **FileFunctionsMapModel** (`file_functions_map.json`) - File-to-function mappings
- **EntryPointModel** (`entry.json`) - Detected application entry points
- **CallChainAnalysisModel** (`call_chain_analysis.json`) - AI-analyzed execution flows
- **FeatureAnalysisModel** (`feature_analysis.json`) - AI-generated feature documentation

### Key Services and Models

**Analysis Services:**
- `CodeDependencyAnalyzer` - Static analysis using Tree-sitter for C# parsing
- `CallChainAnalyzerService` - AI-powered call chain tracing
- `FeatureAnalyzerService` - AI-powered feature documentation generation
- `EntryPointExtractor` - Entry point detection (manual or AI-assisted)

**AI Agent Integration:**
- Uses autogen framework with structured agents
- `entry_point_detector` agent for automatic entry point discovery
- Call chain and feature analysis agents use OpenAI-compatible APIs (configured for Gemini)

### Configuration System
- Environment variables via `.env` file
- `Config` class manages API keys, model settings, and cache paths
- Default model: `gemini-2.5-flash` via OpenAI-compatible API
- Required env vars: `GEMINI_API_KEY`, optional: `GEMINI_MODEL`, `CACHE_PATH`

### File Pattern Recognition
The system is optimized for C# codebases with specific patterns:

- **Include patterns**: `*.cs` files only
- **Exclude patterns**: Test files, documentation, build artifacts (see `EXCLUDE_PATTERNS` in main.py)
- **Entry point detection**: Controllers, Minimal APIs, background services, event handlers, CLI applications

### Caching Strategy
The system implements aggressive caching at every stage:
- Each analysis stage checks for existing results before processing
- Run IDs allow for versioned analysis results
- Cache hits are clearly logged for transparency
- Manual cache invalidation by deleting run directories

### AI Rate Limiting
Built-in rate limiting between AI API calls:
- 60-second delays between sequential AI operations
- Configurable sleep intervals to avoid API quotas
- Progress logging shows current operation status

## Entry Point Specification Format
When manually specifying entry points, use the format:
```
["ClassName.MethodName", "AnotherClass.AnotherMethod"]
```

Example:
```python
appoint_entries = ["ItemController.DeleteAsync", "ClientController.GetAsync"]
```

## Important Implementation Details

### Model Relationships
- All models use dependency injection pattern
- Models are instantiated per `run_id` for data isolation  
- `FileFunctionsMapModel` provides file-to-function lookups for entry point extraction
- `DependencyModel` stores function-level call relationships for chain analysis

### AI Agent Tool System
The system provides AI agents with structured function tools:
- `create_source_code_tools()` - File content retrieval
- `create_dependency_tools()` - Dependency relationship queries
- Tools hide implementation details from AI agents while providing structured data access

### Tree-sitter Integration
C# code parsing uses Tree-sitter with specific query patterns:
- Function definitions, class declarations, interface extraction
- Method call detection with expression context
- Filtering of common framework methods to reduce noise