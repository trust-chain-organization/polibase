# LLM Service Layer

This directory contains the shared service layer for all LLM operations in the Polibase project.

## Overview

The service layer provides a centralized, consistent approach to LLM operations across the entire codebase, reducing duplication and improving maintainability.

## Components

### 1. LLMService (`llm_service.py`)
Central service for managing LLM instances with:
- Lazy initialization
- Consistent configuration
- Built-in retry logic with exponential backoff
- Support for structured outputs
- Pre-configured model instances (fast/advanced)

### 2. PromptManager (`prompt_manager.py`)
Centralized prompt management with:
- All prompts in one place
- Support for LangChain Hub prompts
- Prompt caching for performance
- Easy prompt customization

### 3. ChainFactory (`chain_factory.py`)
Factory for creating LangChain chains with:
- Pre-configured chains for common tasks
- Consistent error handling
- Support for structured outputs
- Generic chain creation

## Benefits

1. **Code Reduction**: ~40% less boilerplate code
2. **Consistency**: Same error handling and retry logic everywhere
3. **Performance**: Reusable chains and connection pooling
4. **Maintainability**: Changes in one place affect all modules
5. **Testability**: Easy to mock services for testing

## Usage Examples

### Basic Usage
```python
from src.services import LLMService, ChainFactory

# Create service
llm_service = LLMService.create_fast_instance()
chain_factory = ChainFactory(llm_service)

# Create and use a chain
chain = chain_factory.create_politician_extractor_chain(PoliticianInfoList)
result = chain_factory.invoke_with_retry(chain, {"minutes": minutes_text})
```

### Advanced Usage
```python
# Use advanced model for complex tasks
llm_service = LLMService.create_advanced_instance(temperature=0.2)

# Create custom chain
chain = chain_factory.create_generic_chain(
    "Extract {data_type} from: {content}",
    output_schema=CustomSchema,
    input_variables=["data_type", "content"]
)
```

## Migration

See `migration_guide.md` for detailed instructions on migrating existing code to use the service layer.

## Refactored Modules

The following modules have been refactored to use the service layer:
- `minutes_divide_processor/minutes_divider_refactored.py`
- `politician_extract_processor/politician_extractor_refactored.py`
- `party_member_extractor/extractor_refactored.py`
- `database/speaker_matching_service_refactored.py`
- `update_speaker_links_llm_refactored.py`

Original files are preserved for backward compatibility during the transition period.