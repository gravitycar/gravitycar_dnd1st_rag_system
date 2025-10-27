#!/usr/bin/env python3
"""
OpenAI Transformer for Table Transformer.

Handles OpenAI API interactions to transform markdown tables into
JSON arrays with descriptive property names. Each data row becomes
a separate JSON object with a title property for heading generation.
"""

import json
import re
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from openai import APIError, RateLimitError, APITimeoutError

logger = logging.getLogger(__name__)


class OpenAITransformer:
    """
    Transforms markdown tables to JSON using OpenAI API.
    
    This class handles:
    - Prompt construction with table and context
    - OpenAI API calls with retry logic
    - JSON extraction and validation
    - Cost calculation
    - Error handling
    """
    
    # Prompt template requesting array output (one JSON object per row)
    PROMPT_TEMPLATE = """You are an expert in giving JSON objects self-documenting, human-friendly property names that describe what the property represents.

I will provide you with a table in markdown format, and text that describes the data the table represents. 

Your task will be to convert the markdown table into an array of JSON objects. You will use the provided text that describes the table to understand what the table's data represents so that the property names you use in the JSON are descriptive and informative. The JSON must be self-documenting so that other LLM's and humans can easily understand it and accurately parse it.

The JSON should follow these exact formatting rules:

- Split the data so that each Data row (from the y-axis) becomes a separate JSON object with the data for that row in an associative array.
- Be aware that the first "data row" may actually be headings. Read the text describing the table carefully to understand the table's structure.
- Do not abbreviate any property names (e.g., write "armor class" instead of "ac").
- IMPORTANT: If a table heading represents a range of values, i.e. 1-3, expand the data to create 1 column for each value in the range.
- Remember that JSON allows property names that are quoted to contain spaces. Quote all property names. Do not replace spaces with underscores when naming properties.
- Each JSON object should include:
    - title: If the context includes a markdown heading, use that heading as the title. Append the y-axis column name and current y-axis row value.
    - description: Plain-english description of the table's data and its purpose.
- The JSON property names should be based on the table headings. They should be descriptive but not verbose. DO NOT ABBREVIATE. Always use associative arrays with keys based on the table headings so that each value has a description.
- Use nested data structures to organize related data logically. Do NOT flatten the data into a single level.
- Convert numeric values to appropriate types (int, float)

Preserve the original data values exactly.

Format the JSON cleanly and consistently.

Return ONLY a JSON array with one object per data row, with no additional explanation or formatting. Do not wrap it in markdown code blocks.

Here is the table:
{table_markdown}

Here is the text that describes the table's purpose:
{table_context}"""
    
    # Pricing per 1M tokens (gpt-4o-mini, October 2024)
    PRICE_PER_1M_INPUT_TOKENS = 0.150
    PRICE_PER_1M_OUTPUT_TOKENS = 0.600
    
    def __init__(
        self, 
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0
    ):
        """
        Initialize OpenAI transformer.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
            temperature: Temperature for generation (default: 0.0 for deterministic)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        logger.info(f"OpenAITransformer initialized with model={model}, temperature={temperature}")
    
    def transform_table(
        self, 
        table_markdown: str,
        table_context: str
    ) -> Tuple[List[Dict[str, Any]], int, float]:
        """
        Transform a markdown table to JSON array using OpenAI.
        
        Args:
            table_markdown: Markdown table to transform
            table_context: Context describing the table
            
        Returns:
            Tuple of (json_objects, tokens_used, cost_usd)
            
        Raises:
            ValueError: If JSON validation fails
            APIError: If OpenAI API call fails after retries
        """
        # Construct prompt
        prompt = self._construct_prompt(table_markdown, table_context)
        
        # DEBUG: Log the full prompt
        logger.info("=" * 80)
        logger.info("FULL PROMPT SENT TO OPENAI:")
        logger.info("=" * 80)
        logger.info(prompt)
        logger.info("=" * 80)
        logger.info(f"Prompt length: {len(prompt)} characters")
        logger.info("=" * 80)
        
        # Call OpenAI with retry logic
        try:
            response, tokens_used = self._call_openai_with_retry(prompt)
            logger.info("=" * 80)
            logger.info("OPENAI RESPONSE:")
            logger.info("=" * 80)
            logger.info(response[:2000] + ("..." if len(response) > 2000 else ""))
            logger.info("=" * 80)
            logger.debug(f"OpenAI response received: {len(response)} chars, {tokens_used} tokens")
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
        
        # Extract and validate JSON
        try:
            json_objects = self._extract_and_validate_json(response)
            logger.info(f"Successfully extracted {len(json_objects)} JSON objects")
        except Exception as e:
            logger.error(f"JSON extraction/validation failed: {e}")
            raise ValueError(f"Failed to extract valid JSON: {e}")
        
        # Calculate cost
        cost = self._calculate_cost(tokens_used)
        logger.debug(f"Transformation cost: ${cost:.6f}")
        
        return json_objects, tokens_used, cost
    
    def _construct_prompt(
        self, 
        table_markdown: str,
        table_context: str
    ) -> str:
        """
        Build prompt from template.
        
        Args:
            table_markdown: Markdown table
            table_context: Context describing table
            
        Returns:
            Formatted prompt string
        """
        return self.PROMPT_TEMPLATE.format(
            table_markdown=table_markdown,
            table_context=table_context
        )
    
    def _call_openai_with_retry(
        self, 
        prompt: str,
        max_retries: int = 3
    ) -> Tuple[str, int]:
        """
        Call OpenAI API with exponential backoff retry logic.
        
        Args:
            prompt: Prompt to send to API
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (response_text, total_tokens_used)
            
        Raises:
            APIError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                logger.debug(f"OpenAI API call attempt {attempt + 1}/{max_retries}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a data transformation expert."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature
                )
                
                # Extract response text and token usage
                response_text = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
                
                logger.info(f"OpenAI API call succeeded on attempt {attempt + 1}")
                return response_text, tokens_used
                
            except RateLimitError as e:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached for rate limit")
                    raise
                    
            except APITimeoutError as e:
                wait_time = 2 ** attempt
                logger.warning(f"API timeout, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached for timeout")
                    raise
                    
            except APIError as e:
                logger.error(f"OpenAI API error: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached for API error")
                    raise
        
        # Should never reach here
        raise APIError("Unexpected: exceeded max retries without raising exception")
    
    def _extract_and_validate_json(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract and validate JSON array from OpenAI response.
        
        Handles:
        - Pure JSON array
        - JSON wrapped in markdown code blocks
        - Single JSON object (wraps in array as fallback)
        - Text before/after JSON
        
        Args:
            response: Raw response from OpenAI
            
        Returns:
            List of JSON objects (validated)
            
        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        # Strip whitespace
        response = response.strip()
        
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            logger.debug("Extracted JSON from markdown code block")
        else:
            # Try to find JSON array directly
            array_match = re.search(r'(\[[\s\S]*\])', response, re.DOTALL)
            if array_match:
                json_str = array_match.group(1)
                logger.debug("Extracted JSON array from response")
            else:
                # Try to find single JSON object (fallback)
                object_match = re.search(r'(\{[\s\S]*\})', response, re.DOTALL)
                if object_match:
                    json_str = f"[{object_match.group(1)}]"  # Wrap in array
                    logger.warning("Found single JSON object, wrapping in array")
                else:
                    raise ValueError("No valid JSON found in response")
        
        # Parse JSON
        try:
            json_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            raise ValueError(f"Invalid JSON: {e}")
        
        # Validate structure
        if not isinstance(json_data, list):
            raise ValueError(f"Expected JSON array, got {type(json_data).__name__}")
        
        if len(json_data) == 0:
            raise ValueError("JSON array is empty")
        
        # Validate each object has required fields
        for i, obj in enumerate(json_data):
            if not isinstance(obj, dict):
                raise ValueError(f"Object {i} is not a dictionary")
            if "title" not in obj:
                raise ValueError(f"Object {i} missing required 'title' field")
        
        logger.info(f"Validated {len(json_data)} JSON objects")
        return json_data
    
    def _calculate_cost(self, tokens_used: int) -> float:
        """
        Calculate cost in USD for token usage.
        
        Approximates input/output split as 70/30 based on typical usage.
        
        Args:
            tokens_used: Total tokens used
            
        Returns:
            Cost in USD
        """
        # Approximate split (70% input, 30% output)
        input_tokens = tokens_used * 0.7
        output_tokens = tokens_used * 0.3
        
        input_cost = (input_tokens / 1_000_000) * self.PRICE_PER_1M_INPUT_TOKENS
        output_cost = (output_tokens / 1_000_000) * self.PRICE_PER_1M_OUTPUT_TOKENS
        
        return input_cost + output_cost
