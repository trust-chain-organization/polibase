"""Factory for creating different types of LangChain chains"""
from typing import Type, Optional, Dict, Any, List
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain import hub
from pydantic import BaseModel
import logging

from .llm_service import LLMService
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class ChainFactory:
    """Factory for creating configured chains for different use cases"""
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        prompt_manager: Optional[PromptManager] = None
    ):
        """
        Initialize chain factory
        
        Args:
            llm_service: LLM service instance (creates default if not provided)
            prompt_manager: Prompt manager instance (creates default if not provided)
        """
        self.llm_service = llm_service or LLMService.create_fast_instance()
        self.prompt_manager = prompt_manager or PromptManager.get_default_instance()
    
    def create_minutes_divider_chain(self, output_schema: Type[BaseModel]) -> Runnable:
        """
        Create chain for dividing minutes into sections
        
        Args:
            output_schema: Schema for section info list
            
        Returns:
            Configured chain
        """
        try:
            # Try to get from hub first
            prompt = self.prompt_manager.get_hub_prompt('divide_chapter_prompt')
        except Exception:
            # Fallback to local prompt
            prompt = self.prompt_manager.get_prompt('minutes_divide')
        
        llm = self.llm_service.get_structured_llm(output_schema)
        
        return {"minutes": RunnablePassthrough()} | prompt | llm
    
    def create_speech_divider_chain(self, output_schema: Type[BaseModel]) -> Runnable:
        """
        Create chain for dividing sections into speeches
        
        Args:
            output_schema: Schema for speaker and speech content list
            
        Returns:
            Configured chain
        """
        try:
            prompt = self.prompt_manager.get_hub_prompt('comment_divide_prompt')
        except Exception:
            prompt = self.prompt_manager.get_prompt('speech_divide')
        
        llm = self.llm_service.get_structured_llm(output_schema)
        
        return {"section_string": RunnablePassthrough()} | prompt | llm
    
    def create_politician_extractor_chain(self, output_schema: Type[BaseModel]) -> Runnable:
        """
        Create chain for extracting politician information
        
        Args:
            output_schema: Schema for politician info list
            
        Returns:
            Configured chain
        """
        try:
            prompt = self.prompt_manager.get_hub_prompt('politician_extraction_prompt')
        except Exception:
            prompt = self.prompt_manager.get_prompt('politician_extract')
        
        llm = self.llm_service.get_structured_llm(output_schema)
        
        return {"minutes": RunnablePassthrough()} | prompt | llm
    
    def create_speaker_matching_chain(self, output_schema: Type[BaseModel]) -> Runnable:
        """
        Create chain for speaker matching with JSON output
        
        Args:
            output_schema: Schema for speaker match result
            
        Returns:
            Configured chain with JSON parsing
        """
        prompt = self.prompt_manager.get_prompt('speaker_match')
        parser = JsonOutputParser(pydantic_object=output_schema)
        
        return prompt | self.llm_service.llm | parser
    
    def create_party_member_extractor_chain(self, output_schema: Type[BaseModel]) -> Runnable:
        """
        Create chain for extracting party member information
        
        Args:
            output_schema: Schema for party member list
            
        Returns:
            Configured chain
        """
        # Party member extraction uses advanced model for better accuracy
        advanced_service = LLMService.create_advanced_instance()
        llm = advanced_service.get_structured_llm(output_schema)
        
        # Direct invocation without chain for party member extraction
        return llm
    
    def create_generic_chain(
        self,
        prompt_template: str,
        output_schema: Optional[Type[BaseModel]] = None,
        input_variables: Optional[List[str]] = None,
        use_json_parser: bool = False
    ) -> Runnable:
        """
        Create a generic chain with custom prompt
        
        Args:
            prompt_template: Custom prompt template
            output_schema: Optional schema for structured output
            input_variables: Variables expected in the prompt
            use_json_parser: Whether to use JSON output parser
            
        Returns:
            Configured chain
        """
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        if output_schema and not use_json_parser:
            llm = self.llm_service.get_structured_llm(output_schema)
        else:
            llm = self.llm_service.llm
        
        # Build input mapping
        if input_variables:
            input_mapping = {var: RunnablePassthrough() for var in input_variables}
            chain = input_mapping | prompt | llm
        else:
            chain = prompt | llm
        
        # Add JSON parser if requested
        if use_json_parser and output_schema:
            parser = JsonOutputParser(pydantic_object=output_schema)
            chain = chain | parser
        
        return chain
    
    def invoke_with_retry(
        self,
        chain: Runnable,
        input_data: Dict[str, Any],
        max_retries: int = 3
    ) -> Any:
        """
        Invoke a chain with retry logic
        
        Args:
            chain: Chain to invoke
            input_data: Input data
            max_retries: Maximum retry attempts
            
        Returns:
            Chain result
        """
        return self.llm_service.invoke_with_retry(chain, input_data, max_retries)