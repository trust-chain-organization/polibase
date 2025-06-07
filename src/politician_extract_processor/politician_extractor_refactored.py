"""Refactored Politician Extractor using shared LLM service layer"""
from typing import Optional
import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from ..services import LLMService, ChainFactory
from .models import (
    PoliticianInfo,
    PoliticianInfoList,
    PoliticianProcessState
)

logger = logging.getLogger(__name__)


class PoliticianExtractor:
    """Politician extractor using centralized LLM services"""
    
    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None, k: int = 5):
        """
        Initialize politician extractor
        
        Args:
            llm: Optional LLM instance for backward compatibility
            k: Number parameter (not currently used)
        """
        self.k = k
        
        # Initialize services
        if llm:
            # Backward compatibility: create service from provided LLM
            self.llm_service = LLMService(
                model_name=llm.model_name,
                temperature=llm.temperature
            )
        else:
            self.llm_service = LLMService.create_fast_instance()
        
        self.chain_factory = ChainFactory(self.llm_service)
        
        # Pre-create chain for performance
        self._extract_chain = self.chain_factory.create_politician_extractor_chain(PoliticianInfoList)

    def politician_extract_run(self, minutes: str) -> PoliticianInfoList:
        """
        Extract politician information from minutes
        
        Args:
            minutes: Minutes text to extract from
            
        Returns:
            PoliticianInfoList with extracted politicians
        """
        try:
            # Use chain factory with retry logic
            result = self.chain_factory.invoke_with_retry(
                self._extract_chain,
                {"minutes": minutes}
            )
            
            # Validate result type
            if not isinstance(result, PoliticianInfoList):
                if isinstance(result, dict):
                    result = PoliticianInfoList(**result)
                elif isinstance(result, list):
                    result = PoliticianInfoList(politician_info_list=result)
                else:
                    logger.error(f"Unexpected result type: {type(result)}")
                    return PoliticianInfoList(politician_info_list=[])
            
            logger.info(f"Extracted {len(result.politician_info_list)} politicians")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting politicians: {e}")
            # Return empty list on error
            return PoliticianInfoList(politician_info_list=[])