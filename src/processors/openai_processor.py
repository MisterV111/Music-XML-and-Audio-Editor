import openai
from openai import OpenAI
from openai import AuthenticationError, APIError, RateLimitError
import logging
from typing import Dict, List, Tuple
from src.config import get_openai_key, OPENAI_MODEL

class OpenAIProcessor:
    """Handles interactions with OpenAI API for interpreting edit commands."""
    
    # Error messages for different scenarios
    ERROR_MESSAGES = {
        "AUTH_ERROR": "Unable to process edit command. Please try again later.",
        "API_ERROR": "Service is temporarily unavailable. Please try again in a few minutes.",
        "PROCESSING_ERROR": "Could not understand the edit command. Please try rephrasing it.",
        "PARSE_ERROR": "Received an invalid response. Please try a simpler command.",
        "INVALID_ACTION": "Please specify a valid action: keep, remove, or reorder.",
        "NO_SECTIONS": "Please specify which sections you want to edit.",
        "INVALID_SECTIONS": "Some sections mentioned are not available in the song.",
        "INVALID_ORDER": "The reordering format is invalid. Please try again.",
        "INVALID_ORDER_SECTIONS": "Some sections in the reordering are not available.",
        "VALIDATION_ERROR": "The command could not be validated. Please try rephrasing it."
    }
    
    def __init__(self):
        """Initialize the OpenAI processor."""
        api_key = get_openai_key()
        self.client = OpenAI(api_key=api_key)
    
    def parse_edit_command(self, command: str, available_sections: List[str]) -> Tuple[Dict, str]:
        """
        Parse a natural language edit command into structured instructions.
        
        Args:
            command: The user's natural language edit command
            available_sections: List of available sections in the song
            
        Returns:
            Tuple of (command_dict, user_message) where command_dict contains the parsed
            instructions and user_message contains a friendly message about the result
        """
        try:
            if not command.strip():
                return (
                    {"error": "Empty command", "code": "PROCESSING_ERROR"},
                    "Please provide an edit command."
                )
            
            # Create a detailed prompt for the API
            prompt = self._create_edit_prompt(command, available_sections)
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a music editor assistant that helps parse edit commands for audio sections."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            # Parse and validate the response
            parsed_command = self._parse_api_response(response.choices[0].message.content)
            validated_command = self._validate_command(parsed_command, available_sections)
            
            # If there's an error, return with user-friendly message
            if "error" in validated_command:
                return (
                    validated_command,
                    self.ERROR_MESSAGES.get(validated_command.get("code", "PROCESSING_ERROR"))
                )
            
            # Create success message
            success_msg = self._create_success_message(validated_command)
            return (validated_command, success_msg)
            
        except AuthenticationError:
            logging.error("OpenAI API authentication failed")
            return (
                {"error": "Internal service error", "code": "AUTH_ERROR"},
                self.ERROR_MESSAGES["AUTH_ERROR"]
            )
        except APIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            return (
                {"error": "Service temporarily unavailable", "code": "API_ERROR"},
                self.ERROR_MESSAGES["API_ERROR"]
            )
        except RateLimitError:
            logging.error("OpenAI API rate limit exceeded")
            return (
                {"error": "Service busy", "code": "API_ERROR"},
                "The service is currently busy. Please try again in a moment."
            )
        except Exception as e:
            logging.error(f"Error parsing edit command: {str(e)}")
            return (
                {"error": "Failed to process edit command", "code": "PROCESSING_ERROR"},
                self.ERROR_MESSAGES["PROCESSING_ERROR"]
            )
    
    def _create_success_message(self, command: Dict) -> str:
        """Create a user-friendly success message based on the command."""
        action = command["action"]
        sections = command["sections"]
        
        if action == "keep":
            return f"Will keep the following sections: {', '.join(sections)}"
        elif action == "remove":
            return f"Will remove the following sections: {', '.join(sections)}"
        return "Command processed successfully."
    
    def _create_edit_prompt(self, command: str, available_sections: List[str]) -> str:
        """Create a detailed prompt for the OpenAI API."""
        return f"""
You are a music editor assistant that understands complex editing instructions for audio sections.

Parse the following edit command for a music editor:
Command: "{command}"

Available sections in order: {', '.join(available_sections)}

Instructions for processing commands:
1. For simple removal instructions:
   - "remove X and Y" means ONLY remove sections X and Y, keeping everything else
   - Example: "remove the Intro and the Outro" means remove ONLY those two sections
   - Do not interpret this as "keep only the Intro and Outro"

2. For range-based commands (e.g., "from X to Y"):
   - Include ALL sections from X through Y in sequential order
   - Example: "remove from Intro to Verse 2" includes [Intro, Verse 1, Chorus 1, Interlude 1, Verse 2]

3. For "keep" commands:
   - These take priority over "remove" commands
   - Any sections specified in a "keep" command should be kept regardless of previous remove commands

4. For mixed instructions:
   - Process instructions in sequence
   - Later "keep" commands override earlier "remove" commands
   - Example: "remove from Intro to Verse 2, keep Chorus 2" will keep Chorus 2 even if it was in the removal range

Return a JSON structure with:
1. "action": The main action (keep/remove)
2. "sections": List of sections to act upon, in the order they appear in the available sections list

Example responses:
For "remove the Intro and the Outro":
{{
    "action": "remove",
    "sections": ["Intro", "Outro"]
}}

For "remove from Intro to Verse 2, keep Chorus 2":
{{
    "action": "keep",
    "sections": ["Chorus 2"]
}}

Important: 
- Use the exact section names as provided in the available sections list
- When processing a range (e.g., "from X to Y"), include all sections between X and Y
- Maintain the original order of sections as they appear in the available sections list
- For simple removal commands, only include the specifically mentioned sections
"""
    
    def _parse_api_response(self, response: str) -> Dict:
        """Parse the API response into a structured format."""
        try:
            import json
            parsed = json.loads(response)
            return parsed
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse API response as JSON: {str(e)}")
            return {"error": "Invalid response format", "code": "PARSE_ERROR"}
    
    def _validate_command(self, command: Dict, available_sections: List[str]) -> Dict:
        """Validate the parsed command against available sections."""
        if "error" in command:
            return command
            
        try:
            # Convert available sections to lowercase and create both space and underscore versions
            available_sections_lower = [s.lower() for s in available_sections]
            available_sections_underscore = [s.lower().replace(' ', '_') for s in available_sections]
            
            # Debug logging
            logging.debug(f"Available sections: {available_sections}")
            logging.debug(f"Command to validate: {command}")
            
            # Validate action
            if "action" not in command or command["action"] not in ["keep", "remove"]:
                logging.debug(f"Invalid action: {command.get('action')}")
                return {"error": "Invalid action specified", "code": "INVALID_ACTION"}
                
            # Validate sections
            if "sections" not in command or not command["sections"]:
                logging.debug("No sections specified in command")
                return {"error": "No sections specified", "code": "NO_SECTIONS"}
            
            # Check if all sections exist (case-insensitive, allowing both space and underscore format)
            command_sections = [s.lower() for s in command["sections"]]
            command_sections_space = [s.replace('_', ' ') for s in command_sections]
            
            logging.debug(f"Command sections (lowercase): {command_sections}")
            logging.debug(f"Command sections (with spaces): {command_sections_space}")
            logging.debug(f"Available sections (lowercase): {available_sections_lower}")
            
            invalid_sections = [s for s in command_sections_space if s not in available_sections_lower]
            
            logging.debug(f"Invalid sections found: {invalid_sections}")
            
            if invalid_sections:
                return {
                    "error": f"Invalid sections specified: {', '.join(invalid_sections)}", 
                    "code": "INVALID_SECTIONS"
                }
            
            # Map the sections back to their original case
            section_map = {s.lower(): s for s in available_sections}
            command["sections"] = [section_map[s.replace('_', ' ').lower()] for s in command["sections"]]
            
            return command
            
        except Exception as e:
            logging.error(f"Error validating command: {str(e)}")
            return {"error": "Command validation failed", "code": "VALIDATION_ERROR"} 