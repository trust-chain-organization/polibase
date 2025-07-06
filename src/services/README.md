# LLM Service Layer

This directory contains the centralized service layer for all LLM operations in the Polibase project.

## Overview

The service layer provides a unified, consistent approach to LLM operations across the entire codebase, with centralized prompt management, error handling, and configuration.

## Architecture

### Core Components

#### 1. LLMService (`llm_service.py`)
Central service for managing all LLM operations:
- **Unified Interface**: Single point of entry for all LLM calls
- **Rate Limiting**: Built-in rate limiting to prevent API quota issues
- **Retry Logic**: Automatic retry with exponential backoff
- **Error Handling**: Centralized error conversion and handling
- **Structured Output**: Native support for Pydantic models
- **Prompt Integration**: Seamless integration with prompt management

#### 2. LLMServiceFactory (`llm_factory.py`)
Factory pattern for creating configured LLMService instances:
- **Presets**: Fast, Advanced, Creative, Precise, Legacy
- **Caching**: Reuses instances for better performance
- **Custom Configuration**: Override any settings
- **Model Management**: Centralized model selection

#### 3. Prompt Management
- **PromptLoader** (`prompt_loader.py`): Loads prompts from YAML files
- **PromptManager** (`prompt_manager.py`): Legacy in-code prompts (being phased out)
- **External Prompts**: All prompts stored in `src/prompts/*.yaml`

#### 4. Error Types (`llm_errors.py`)
Specific error types for better handling:
- `LLMRateLimitError`: Rate limit exceeded
- `LLMTimeoutError`: Request timeout
- `LLMInvalidResponseError`: Parsing errors
- `LLMAuthenticationError`: API key issues
- `LLMQuotaExceededError`: Quota limits

#### 5. ChainFactory (`chain_factory.py`)
Pre-configured chains for common operations:
- Speaker matching chains
- Politician extraction chains
- Generic chain creation
- Consistent error handling

## Benefits

1. **Consistency**: All LLM operations use the same patterns
2. **Reliability**: Built-in retry and rate limiting
3. **Maintainability**: Centralized configuration and prompts
4. **Testability**: Comprehensive mock framework
5. **Performance**: Connection pooling and caching
6. **Flexibility**: Easy to switch models or add new ones

## Usage Examples

### Basic Usage
```python
from src.services.llm_factory import LLMServiceFactory

# Create service with factory
factory = LLMServiceFactory()
service = factory.create_fast()  # For simple tasks
# or
service = factory.create_advanced()  # For complex tasks

# Use with prompts
result = service.invoke_prompt(
    "speaker_match",
    {"speaker_name": "田中太郎", "available_speakers": "..."}
)
```

### With Structured Output
```python
from pydantic import BaseModel

class ExtractedData(BaseModel):
    name: str
    value: int

result = service.invoke_prompt(
    "data_extraction",
    {"content": "some text"},
    output_schema=ExtractedData
)
```

### Custom Chain Creation
```python
chain = service.create_simple_chain(
    prompt_key="custom_prompt",
    output_schema=MySchema
)
result = service.invoke_with_retry(chain, {"input": "data"})
```

## Testing

### Mock Framework
```python
from src.test_utils.llm_mock import mock_llm_service

@mock_llm_service([{"field": "value"}])
def test_function(mock_llm):
    # LLM calls return mocked responses
    result = my_function()
    assert mock_llm.call_count == 1
```

### Context Manager
```python
from src.test_utils.llm_mock import LLMServiceMock

with LLMServiceMock(["response"]) as mock:
    result = my_function()
    assert mock.call_history[0]["method"] == "invoke"
```

## Migration Status

✅ **Completed Migrations:**
- `minutes_divider.py`: Full LLMService integration
- `speaker_matching_service.py`: Using LLMService
- `politician_matching_service.py`: Migrated to LLMService
- `party_member_extractor/`: Using LLMService
- `conference_member_extractor/`: Already using LLMService
- `update_speaker_links_llm.py`: Updated to use LLMService

## Best Practices

1. **Always use the factory** to create service instances
2. **Define prompts in YAML** files, not in code
3. **Use structured output** when possible for type safety
4. **Handle specific errors** (e.g., `LLMRateLimitError`)
5. **Choose appropriate presets** based on task complexity
6. **Use mocks in tests** to avoid API calls

## Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Required for Gemini API access

### Model Presets
- **Fast**: `gemini-1.5-flash` - For simple, quick tasks
- **Advanced**: `gemini-2.0-flash-exp` - For complex reasoning
- **Creative**: Higher temperature for creative outputs
- **Precise**: Zero temperature for deterministic results
- **Legacy**: Backward compatibility mode
