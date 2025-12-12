import logging
from openai import AsyncOpenAI
from typing import List, Dict, Optional
import base64

logger = logging.getLogger("llm-service")

class LLMService:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model_name = model
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def chat(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1) -> str:
        """Send a chat completion request"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            # Generate response
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def analyze_image(self, image_data: bytes, prompt: str) -> str:
        """Analyze an image using GPT-4 Vision"""
        try:
            # Convert bytes to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"OpenAI Vision API error: {e}")
            raise
    
    async def analyze_image_from_base64(self, base64_image: str, prompt: str) -> str:
        """Analyze an image from base64 string"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            raise
    
    async def generate_code(self, task_description: str, data_info: str) -> str:
        """Generate Python code to solve a data analysis task"""
        system_prompt = """You are an expert Python programmer specializing in data analysis.
Generate clean, efficient Python code using pandas, numpy, and other standard libraries.
The code should be production-ready and handle edge cases."""
        
        prompt = f"""Generate Python code for this task:
Task: {task_description}
Data Info: {data_info}
Requirements:
- Assume data is loaded in a variable called 'df' (pandas DataFrame)
- Use pandas, numpy for analysis
- Store final answer in a variable called 'result'
- Include error handling
- Be precise and accurate
Return ONLY the Python code, no explanations or markdown."""

        code = await self.chat(prompt, system_prompt, temperature=0.0)
        
        # Clean up code - remove markdown if present
        code = code.replace("```python", "").replace("```", "").strip()
        
        return code
    
    async def execute_code_safely(self, code: str, data: Dict) -> any:
        """Execute generated code in a controlled environment"""
        try:
            # Create execution namespace
            namespace = {
                'df': data.get('df'),
                'pd': __import__('pandas'),
                'np': __import__('numpy'),
                'result': None
            }
            
            # Execute code
            exec(code, namespace)
            
            return namespace.get('result')
        
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            raise
