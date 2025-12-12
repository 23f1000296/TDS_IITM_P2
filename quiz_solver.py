import asyncio
import logging
import base64
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import aiohttp
from playwright.async_api import async_playwright, Browser, Page

from llm_service import LLMService
from data_processor import DataProcessor

logger = logging.getLogger("quiz-solver")

class QuizSolver:
    def __init__(self, email: str, secret: str, openai_api_key: str):
        self.email = email
        self.secret = secret
        self.llm = LLMService(openai_api_key)
        self.data_processor = DataProcessor(self.llm)
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    async def initialize(self):
        """Initialize browser and resources"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        logger.info("Browser initialized")
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Resources cleaned up")
    
    async def fetch_quiz_page(self, url: str) -> str:
        """Fetch and render quiz page with JavaScript execution"""
        page = await self.browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # Let JS execute
            content = await page.content()
            return content
        finally:
            await page.close()
    
    def extract_question_from_html(self, html: str) -> str:
        """Extract question text from HTML, handling base64 encoding"""
        # Look for base64 encoded content in atob() calls
        atob_pattern = r'atob\([\'"]([^\'"]+)[\'"]\)'
        matches = re.findall(atob_pattern, html)
        
        if matches:
            try:
                # Decode base64 content
                decoded = base64.b64decode(matches[0]).decode('utf-8')
                return decoded
            except Exception as e:
                logger.warning(f"Failed to decode base64: {e}")
        
        # Fallback: extract text from common containers
        text_patterns = [
            r'<div[^>]*id=["\']result["\'][^>]*>(.*?)</div>',
            r'<div[^>]*class=["\']question["\'][^>]*>(.*?)</div>',
            r'<body[^>]*>(.*?)</body>'
        ]
        
        for pattern in text_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', match.group(1))
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 10:
                    return text
        
        return html[:2000]  # Return first 2000 chars as fallback
    
    async def parse_question(self, question_text: str) -> Dict[str, Any]:
        """Use LLM to parse and understand the question"""
        prompt = f"""Parse this quiz question and extract key information.
Question:
{question_text}
Provide a JSON response with:
- task_type: (download_file, web_scraping, data_analysis, api_call, visualization, text_processing)
- files_to_download: list of URLs to download
- submit_url: URL where answer should be submitted
- answer_format: (number, string, boolean, json, base64_image)
- analysis_required: description of what analysis is needed
- expected_answer_key: the key name for the answer field (usually "answer")
Return only valid JSON, no markdown or explanations."""

        response = await self.llm.chat(prompt)
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Return a safe default
            return {
                "task_type": "unknown",
                "files_to_download": [],
                "submit_url": None,
                "answer_format": "string",
                "analysis_required": question_text,
                "expected_answer_key": "answer"
            }
    
    async def solve_question(self, question_text: str, parsed_info: Dict[str, Any]) -> Any:
        """Solve the question based on parsed information"""
        task_type = parsed_info.get("task_type", "unknown")
        
        logger.info(f"Solving question of type: {task_type}")
        
        # Download any required files
        downloaded_files = []
        for file_url in parsed_info.get("files_to_download", []):
            try:
                file_data = await self.data_processor.download_file(file_url)
                downloaded_files.append(file_data)
            except Exception as e:
                logger.error(f"Failed to download {file_url}: {e}")
        
        # Use LLM to analyze and solve
        context = f"""Question: {question_text}
Task Type: {task_type}
Analysis Required: {parsed_info.get('analysis_required', 'Not specified')}
"""
        if downloaded_files:
            context += f"\nDownloaded {len(downloaded_files)} file(s).\n"
            for i, file_data in enumerate(downloaded_files):
                context += f"\nFile {i+1} Info:\n{file_data.get('summary', 'No summary')}\n"
        
        context += f"""
Based on this information, provide the FINAL ANSWER in the format: {parsed_info.get('answer_format')}
If the answer is a number, return just the number.
If it's a calculation, show the calculation and then give the final number.
Be precise and accurate."""

        answer_response = await self.llm.chat(context)
        
        # Extract answer based on format
        answer_format = parsed_info.get("answer_format", "string")
        answer = self.extract_answer(answer_response, answer_format)
        
        return answer
    
    def extract_answer(self, response: str, answer_format: str) -> Any:
        """Extract the answer from LLM response based on expected format"""
        if answer_format == "number":
            # Extract first number found
            numbers = re.findall(r'-?\d+\.?\d*', response)
            if numbers:
                num = numbers[-1]  # Take last number (likely the final answer)
                return float(num) if '.' in num else int(num)
        
        elif answer_format == "boolean":
            response_lower = response.lower()
            if "true" in response_lower or "yes" in response_lower:
                return True
            return False
        
        elif answer_format == "json":
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
        
        # Default: return cleaned string
        return response.strip()
    
    async def submit_answer(self, submit_url: str, answer: Any, quiz_url: str, answer_key: str = "answer") -> Dict[str, Any]:
        """Submit answer to the specified endpoint"""
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            answer_key: answer
        }
        
        logger.info(f"Submitting answer to {submit_url}: {answer}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(submit_url, json=payload, timeout=30) as response:
                    result = await response.json()
                    logger.info(f"Submission response: {result}")
                    return result
            except Exception as e:
                logger.error(f"Failed to submit answer: {e}")
                return {"correct": False, "error": str(e)}
    
    async def solve_single_quiz(self, quiz_url: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Solve a single quiz.
        Returns: (success, next_url, error_message)
        """
        try:
            # Step 1: Fetch the quiz page
            logger.info(f"Fetching quiz page: {quiz_url}")
            html_content = await self.fetch_quiz_page(quiz_url)
            
            # Step 2: Extract question
            question_text = self.extract_question_from_html(html_content)
            logger.info(f"Extracted question: {question_text[:200]}...")
            
            # Step 3: Parse question using LLM
            parsed_info = await self.parse_question(question_text)
            logger.info(f"Parsed info: {parsed_info}")
            
            # Step 4: Solve the question
            answer = await self.solve_question(question_text, parsed_info)
            logger.info(f"Generated answer: {answer}")
            
            # Step 5: Submit answer
            submit_url = parsed_info.get("submit_url")
            if not submit_url:
                # Try to extract submit URL from question text
                url_pattern = r'https?://[^\s<>"]+/submit[^\s<>"]*'
                urls = re.findall(url_pattern, question_text)
                if urls:
                    submit_url = urls[0]
                else:
                    logger.error("Could not find submit URL")
                    return False, None, "No submit URL found"
            
            answer_key = parsed_info.get("expected_answer_key", "answer")
            result = await self.submit_answer(submit_url, answer, quiz_url, answer_key)
            
            # Step 6: Check result and get next URL
            is_correct = result.get("correct", False)
            next_url = result.get("url")
            reason = result.get("reason")
            
            if is_correct:
                logger.info("Answer correct!")
                return True, next_url, None
            else:
                logger.warning(f"Answer incorrect: {reason}")
                return False, next_url, reason
                
        except Exception as e:
            logger.exception(f"Error solving quiz: {e}")
            return False, None, str(e)
    
    async def solve_quiz_chain(self, initial_url: str, start_time: datetime):
        """Solve a chain of quizzes within the 3-minute time limit"""
        current_url = initial_url
        quiz_count = 0
        max_time = timedelta(minutes=3)
        
        while current_url:
            quiz_count += 1
            elapsed = datetime.now() - start_time
            
            if elapsed > max_time:
                logger.warning("Time limit exceeded (3 minutes)")
                break
            
            logger.info(f"Solving quiz #{quiz_count}: {current_url}")
            
            success, next_url, error = await self.solve_single_quiz(current_url)
            
            if success and next_url:
                logger.info(f"Moving to next quiz: {next_url}")
                current_url = next_url
            elif success and not next_url:
                logger.info("Quiz chain completed successfully!")
                break
            else:
                # Try to retry if we have time and got a next_url
                if next_url and elapsed < max_time:
                    logger.info("Attempting to move to next quiz despite error")
                    current_url = next_url
                else:
                    logger.error(f"Failed to solve quiz: {error}")
                    break
        
        logger.info(f"Completed {quiz_count} quizzes in {datetime.now() - start_time}")
