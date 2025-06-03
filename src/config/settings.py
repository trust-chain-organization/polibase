"""Centralized configuration management using environment variables"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    def __init__(self):
        # Database configuration
        self.database_url = os.getenv(
            'DATABASE_URL',
            'postgresql://polibase_user:polibase_password@localhost:5432/polibase_db'
        )
        
        # API Keys
        self.google_api_key = os.getenv('GOOGLE_API_KEY', '')
        self.langchain_api_key = os.getenv('LANGCHAIN_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
        # LangChain configuration
        self.langchain_tracing_v2 = os.getenv('LANGCHAIN_TRACING_V2', 'false').lower() == 'true'
        self.langchain_endpoint = os.getenv('LANGCHAIN_ENDPOINT', '')
        self.langchain_project = os.getenv('LANGCHAIN_PROJECT', '')
        
        # Application paths
        self.default_pdf_path = os.getenv('DEFAULT_PDF_PATH', 'data/minutes.pdf')
        self.output_dir = os.getenv('OUTPUT_DIR', 'data/output')
        
        # LLM Model settings
        self.llm_model = os.getenv('LLM_MODEL', 'gemini-2.0-flash')
        self.llm_temperature = float(os.getenv('LLM_TEMPERATURE', '0.0'))
        
    def validate(self) -> None:
        """Validate required settings"""
        if not self.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is required. Please set it in your .env file or environment variables."
            )
        
    def get_database_url(self) -> str:
        """Get the appropriate database URL based on environment"""
        # Check if running in Docker
        if os.path.exists('/.dockerenv'):
            # Use Docker service name
            return 'postgresql://polibase_user:polibase_password@postgres:5432/polibase_db'
        return self.database_url
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled"""
        return os.getenv('DEBUG', 'false').lower() == 'true'

# Global settings instance
settings = Settings()

# Utility function to get settings
def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings