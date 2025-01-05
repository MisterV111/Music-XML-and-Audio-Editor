import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Get API key from environment variable
OPENAI_MODEL = "gpt-3.5-turbo"

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Audio Processing Configuration
FADE_DURATION = 300  # Default fade duration in milliseconds
SUPPORTED_AUDIO_FORMATS = ['wav', 'mp3']

# Export Configuration
DEFAULT_EXPORT_FORMAT = 'wav'
EXPORT_SAMPLE_RATE = 44100
EXPORT_CHANNELS = 2

# Error messages
CONFIG_ERRORS = {
    "NO_API_KEY": "OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable.",
    "INVALID_API_KEY": "OpenAI API key appears to be invalid",
    "INVALID_MODEL": "Specified OpenAI model is not supported"
}

def get_openai_key() -> str:
    """
    Get the OpenAI API key with validation.
    
    Returns:
        str: The API key if valid
        
    Raises:
        ValueError: If the API key is not configured or appears invalid
    """
    api_key = OPENAI_API_KEY
    if not api_key:
        logging.error(CONFIG_ERRORS["NO_API_KEY"])
        raise ValueError(CONFIG_ERRORS["NO_API_KEY"])
        
    if len(api_key) < 20:  # Basic validation
        logging.error(CONFIG_ERRORS["INVALID_API_KEY"])
        raise ValueError(CONFIG_ERRORS["INVALID_API_KEY"])
        
    return api_key

def get_openai_model() -> str:
    """
    Get the configured OpenAI model with validation.
    
    Returns:
        str: The model name if valid
        
    Raises:
        ValueError: If the model is not supported
    """
    supported_models = ["gpt-3.5-turbo", "gpt-4"]  # Add more as needed
    if OPENAI_MODEL not in supported_models:
        logging.error(CONFIG_ERRORS["INVALID_MODEL"])
        raise ValueError(CONFIG_ERRORS["INVALID_MODEL"])
    return OPENAI_MODEL

def validate_audio_config() -> bool:
    """Validate audio processing configuration."""
    if FADE_DURATION < 0:
        logging.error("Invalid fade duration")
        return False
    if not SUPPORTED_AUDIO_FORMATS:
        logging.error("No supported audio formats configured")
        return False
    return True

def validate_export_config() -> bool:
    """Validate export configuration."""
    if EXPORT_SAMPLE_RATE <= 0:
        logging.error("Invalid export sample rate")
        return False
    if EXPORT_CHANNELS <= 0:
        logging.error("Invalid export channels")
        return False
    if DEFAULT_EXPORT_FORMAT not in SUPPORTED_AUDIO_FORMATS:
        logging.error("Default export format not in supported formats")
        return False
    return True

def validate_all_config() -> bool:
    """Validate all configuration settings."""
    try:
        get_openai_key()
        get_openai_model()
        return all([
            validate_audio_config(),
            validate_export_config()
        ])
    except ValueError:
        return False 