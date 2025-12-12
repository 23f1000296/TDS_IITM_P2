import logging
import aiohttp
import io
import pandas as pd
import pdfplumber
from typing import Dict, Any, Optional
import base64
from pathlib import Path

logger = logging.getLogger("data-processor")

class DataProcessor:
    def __init__(self, llm_service):
        self.llm = llm_service
    
    async def download_file(self, url: str) -> Dict[str, Any]:
        """Download a file and process it based on type"""
        logger.info(f"Downloading file: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as response:
                content = await response.read()
                content_type = response.headers.get('content-type', '')
                
                # Determine file type
                if 'pdf' in content_type or url.endswith('.pdf'):
                    return await self.process_pdf(content, url)
                elif 'csv' in content_type or url.endswith('.csv'):
                    return await self.process_csv(content, url)
                elif 'excel' in content_type or url.endswith(('.xlsx', '.xls')):
                    return await self.process_excel(content, url)
                elif 'image' in content_type or url.endswith(('.png', '.jpg', '.jpeg')):
                    return await self.process_image(content, url)
                elif 'json' in content_type or url.endswith('.json'):
                    return await self.process_json(content, url)
                else:
                    return await self.process_text(content, url)
    
    async def process_pdf(self, content: bytes, url: str) -> Dict[str, Any]:
        """Process PDF file"""
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text_content = []
                tables = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    text = page.extract_text()
                    if text:
                        text_content.append(f"Page {page_num}:\n{text}")
                    
                    # Extract tables
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            tables.append({
                                'page': page_num,
                                'data': table
                            })
                
                # Convert tables to DataFrames
                dataframes = []
                for table_info in tables:
                    try:
                        df = pd.DataFrame(table_info['data'][1:], columns=table_info['data'][0])
                        dataframes.append({
                            'page': table_info['page'],
                            'df': df
                        })
                    except Exception as e:
                        logger.warning(f"Failed to convert table to DataFrame: {e}")
                
                summary = f"PDF with {len(pdf.pages)} pages\n"
                summary += f"Extracted {len(tables)} tables\n"
                summary += "\n".join(text_content[:500])  # First 500 chars
                
                return {
                    'type': 'pdf',
                    'url': url,
                    'text': "\n\n".join(text_content),
                    'tables': dataframes,
                    'summary': summary
                }
        
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            return {'type': 'pdf', 'url': url, 'error': str(e)}
    
    async def process_csv(self, content: bytes, url: str) -> Dict[str, Any]:
        """Process CSV file"""
        try:
            df = pd.read_csv(io.BytesIO(content))
            
            summary = f"CSV file with {len(df)} rows and {len(df.columns)} columns\n"
            summary += f"Columns: {', '.join(df.columns)}\n"
            summary += f"First 5 rows:\n{df.head()}\n"
            summary += f"Data types:\n{df.dtypes}\n"
            
            return {
                'type': 'csv',
                'url': url,
                'df': df,
                'summary': summary,
                'shape': df.shape,
                'columns': list(df.columns)
            }
        
        except Exception as e:
            logger.error(f"CSV processing error: {e}")
            return {'type': 'csv', 'url': url, 'error': str(e)}
    
    async def process_excel(self, content: bytes, url: str) -> Dict[str, Any]:
        """Process Excel file"""
        try:
            excel_file = pd.ExcelFile(io.BytesIO(content))
            sheets = {}
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheets[sheet_name] = df
            
            summary = f"Excel file with {len(sheets)} sheets\n"
            for sheet_name, df in sheets.items():
                summary += f"\nSheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns\n"
                summary += f"Columns: {', '.join(df.columns)}\n"
            
            return {
                'type': 'excel',
                'url': url,
                'sheets': sheets,
                'summary': summary
            }
        
        except Exception as e:
            logger.error(f"Excel processing error: {e}")
            return {'type': 'excel', 'url': url, 'error': str(e)}
    
    async def process_image(self, content: bytes, url: str) -> Dict[str, Any]:
        """Process image file"""
        try:
            # Convert to base64 for storage
            b64_image = base64.b64encode(content).decode('utf-8')
            
            # Analyze with GPT-4o Vision (pass bytes directly)
            prompt = "Describe this image in detail. If it contains text, transcribe it. If it contains data or charts, describe the data."
            
            description = await self.llm.analyze_image(content, prompt)
            
            return {
                'type': 'image',
                'url': url,
                'base64': b64_image,
                'description': description,
                'summary': f"Image analyzed. Description: {description}"
            }
        
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return {'type': 'image', 'url': url, 'error': str(e)}
    
    async def process_json(self, content: bytes, url: str) -> Dict[str, Any]:
        """Process JSON file"""
        try:
            import json
            data = json.loads(content.decode('utf-8'))
            
            summary = f"JSON file\n"
            summary += f"Type: {type(data).__name__}\n"
            
            if isinstance(data, dict):
                summary += f"Keys: {', '.join(data.keys())}\n"
            elif isinstance(data, list):
                summary += f"List with {len(data)} items\n"
            
            return {
                'type': 'json',
                'url': url,
                'data': data,
                'summary': summary
            }
        
        except Exception as e:
            logger.error(f"JSON processing error: {e}")
            return {'type': 'json', 'url': url, 'error': str(e)}
    
    async def process_text(self, content: bytes, url: str) -> Dict[str, Any]:
        """Process text file"""
        try:
            text = content.decode('utf-8')
            
            return {
                'type': 'text',
                'url': url,
                'text': text,
                'summary': f"Text file with {len(text)} characters\n{text[:500]}"
            }
        
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            return {'type': 'text', 'url': url, 'error': str(e)}
    
    async def analyze_data(self, data: Dict[str, Any], question: str) -> Any:
        """Use LLM to analyze data and answer question"""
        
        # Prepare data summary for LLM
        if data.get('type') == 'csv' or data.get('type') == 'excel':
            df = data.get('df') or list(data.get('sheets', {}).values())[0]
            
            # Generate analysis code
            data_info = f"DataFrame with shape {df.shape}, columns: {list(df.columns)}"
            code = await self.llm.generate_code(question, data_info)
            
            # Execute code
            result = await self.llm.execute_code_safely(code, {'df': df})
            return result
        
        elif data.get('type') == 'pdf':
            # Use LLM to answer based on text
            prompt = f"Based on this PDF content, answer the question.\n\nContent:\n{data.get('text', '')[:3000]}\n\nQuestion: {question}\n\nProvide a precise answer."
            answer = await self.llm.chat(prompt)
            return answer
        
        else:
            # Generic analysis
            prompt = f"Based on this data, answer the question.\n\nData Summary:\n{data.get('summary', '')}\n\nQuestion: {question}\n\nProvide a precise answer."
            answer = await self.llm.chat(prompt)
            return answer
