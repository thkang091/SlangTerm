import openai
import os
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Dict, Optional, Any
from config import OPENAI_API_KEY, GPT_MODEL
import requests


# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Check for free/open-source alternative if specified
USE_OPEN_SOURCE_MODEL = os.getenv("USE_OPEN_SOURCE_MODEL", "false").lower() == "true"

class AIService:
    def __init__(self, model=GPT_MODEL):
        self.model = model
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_explanation(self, term: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Generate an explanation for a slang term using GPT-4"""
        context_prompt = f" in the context of {context}" if context else ""
        
        prompt = f"""
        Explain the slang term "{term}"{context_prompt} in a way that's easy for non-native speakers to understand.
        
        Include:
        1. A clear definition
        2. The origin if you know it
        3. 3 example sentences showing proper usage
        4. Pronunciation guide if relevant
        5. Part of speech
        6. Alternative spellings or variations if any exist
        
        Format your response as a JSON object with these keys: 
        "meaning", "origin", "examples", "pronunciation", "part_of_speech", "alternative_spellings"
        
        If you're uncertain about any aspect, use "unknown" as the value.
        """
        
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in explaining slang terms to international students learning English."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        try:
            # Parse the JSON response
            explanation = response.choices[0].message.content
            return explanation
        except Exception as e:
            # Handle parsing errors
            return {
                "meaning": f"Failed to generate explanation for '{term}'",
                "origin": "unknown",
                "examples": [],
                "pronunciation": "unknown",
                "part_of_speech": "unknown",
                "alternative_spellings": []
            }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def translate_slang(
        self, 
        term: str, 
        target_language: str, 
        meaning: Optional[str] = None, 
        examples: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Translate a slang term to another language with contextual examples"""
        meaning_prompt = f"with the meaning: {meaning}" if meaning else ""
        examples_prompt = ""
        if examples and len(examples) > 0:
            examples_str = "\n".join([f"- {example}" for example in examples])
            examples_prompt = f"\nHere are some example usages in English:\n{examples_str}"
        
        prompt = f"""
        Translate the English slang term "{term}" {meaning_prompt} into {target_language}.
        {examples_prompt}
        
        Provide:
        1. The closest equivalent slang or expression in {target_language}
        2. A literal translation if different from the slang equivalent
        3. 2-3 example sentences in {target_language} showing proper usage
        
        Format your response as a JSON object with these keys:
        "translation", "literal_translation", "examples"
        """
        
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a helpful assistant specialized in translating slang terms from English to {target_language}."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        try:
            # Parse the JSON response
            translation = response.choices[0].message.content
            return translation
        except Exception as e:
            # Handle parsing errors
            return {
                "translation": f"Failed to translate '{term}' to {target_language}",
                "literal_translation": "unknown",
                "examples": []
            }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def moderate_submission(self, term: str, meaning: str, examples: List[str]) -> Dict[str, Any]:
        """Check if a user submission is appropriate and likely accurate"""
        examples_str = "\n".join([f"- {example}" for example in examples]) if examples else "None provided"
        
        prompt = f"""
        Review this slang term submission:
        
        Term: {term}
        Meaning: {meaning}
        Examples: 
        {examples_str}
        
        Please evaluate:
        1. If this contains inappropriate content (profanity, hate speech, explicit content, etc.)
        2. If the meaning seems accurate based on your knowledge
        3. If the examples match the provided meaning
        4. Any suggestions for improving the submission
        
        Format your response as a JSON object with these keys:
        "is_appropriate" (boolean), "is_accurate" (boolean), "examples_match" (boolean), "suggestions" (string), "confidence" (float between 0-1)
        """
        
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that moderates slang term submissions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        try:
            # Parse the JSON response
            moderation = response.choices[0].message.content
            return moderation
        except Exception as e:
            # Handle parsing errors
            return {
                "is_appropriate": False,
                "is_accurate": False,
                "examples_match": False,
                "suggestions": f"Failed to moderate submission: {str(e)}",
                "confidence": 0.0
            }
        

    async def fetch_from_urban_dictionary(term: str) -> Dict[str, Any]:
        """Fetch definition from Urban Dictionary API"""
        url = f"https://api.urbandictionary.com/v0/define?term={term}"
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if not data.get("list"):
                return {
                    "meaning": f"No definition found for '{term}'",
                    "examples": [],
                    "origin": "unknown"
                }
            
            # Get the top definition (highest thumbs up)
            top_def = max(data["list"], key=lambda x: x.get("thumbs_up", 0))
            
            return {
                "meaning": top_def.get("definition", ""),
                "examples": [top_def.get("example", "")] if top_def.get("example") else [],
                "origin": "Urban Dictionary",
                "created_at": top_def.get("written_on")
            }
            
        except Exception as e:
            return {
                "meaning": f"Error fetching definition: {str(e)}",
                "examples": [],
                "origin": "unknown"
            }



# Create a singleton instance
ai_service = AIService()