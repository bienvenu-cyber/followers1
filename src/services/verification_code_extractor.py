"""
Advanced verification code extraction with multiple patterns and fallback methods.
"""

import re
import html
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging


class ExtractionMethod(Enum):
    """Methods used for code extraction."""
    REGEX_PATTERN = "regex_pattern"
    HTML_PARSING = "html_parsing"
    JSON_PARSING = "json_parsing"
    KEYWORD_SEARCH = "keyword_search"
    FALLBACK = "fallback"


@dataclass
class ExtractionResult:
    """Result of verification code extraction."""
    code: Optional[str] = None
    confidence: float = 0.0
    method: Optional[ExtractionMethod] = None
    pattern_used: Optional[str] = None
    source_field: Optional[str] = None


class VerificationCodeExtractor:
    """
    Advanced verification code extractor with multiple patterns and fallback methods.
    Supports various email formats and extraction strategies.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Primary regex patterns ordered by confidence
        self.primary_patterns = [
            # Instagram specific patterns
            (r'instagram[^0-9]*(\d{6})', 0.95, "instagram_6digit"),
            (r'verification[^0-9]*code[^0-9]*(\d{6})', 0.90, "verification_code_6digit"),
            (r'confirm[^0-9]*code[^0-9]*(\d{6})', 0.90, "confirm_code_6digit"),
            
            # Generic high-confidence patterns
            (r'(\d{6})[^0-9]*is[^0-9]*your[^0-9]*code', 0.85, "6digit_is_your_code"),
            (r'your[^0-9]*code[^0-9]*is[^0-9]*(\d{6})', 0.85, "your_code_is_6digit"),
            (r'code[:\s]*(\d{6})', 0.80, "code_colon_6digit"),
            
            # 4-digit codes
            (r'verification[^0-9]*code[^0-9]*(\d{4})', 0.75, "verification_code_4digit"),
            (r'(\d{4})[^0-9]*is[^0-9]*your[^0-9]*code', 0.75, "4digit_is_your_code"),
            (r'your[^0-9]*code[^0-9]*is[^0-9]*(\d{4})', 0.75, "your_code_is_4digit"),
            
            # 8-digit codes
            (r'verification[^0-9]*code[^0-9]*(\d{8})', 0.70, "verification_code_8digit"),
            (r'(\d{8})[^0-9]*is[^0-9]*your[^0-9]*code', 0.70, "8digit_is_your_code"),
            
            # Generic patterns (lower confidence)
            (r'\b(\d{6})\b', 0.60, "generic_6digit"),
            (r'\b(\d{4})\b', 0.50, "generic_4digit"),
            (r'\b(\d{8})\b', 0.55, "generic_8digit"),
        ] 
       
        # Fallback patterns for edge cases
        self.fallback_patterns = [
            (r'(\d{5})', 0.40, "5digit_fallback"),
            (r'(\d{7})', 0.45, "7digit_fallback"),
            (r'(\d{3,9})', 0.30, "generic_digit_fallback"),
        ]
        
        # Keywords that increase confidence when found near codes
        self.confidence_keywords = [
            'verification', 'verify', 'confirm', 'code', 'instagram', 
            'authenticate', 'login', 'signup', 'register', 'otp',
            'one-time', 'temporary', 'security'
        ]
        
        # Keywords that decrease confidence
        self.negative_keywords = [
            'phone', 'zip', 'postal', 'year', 'date', 'time',
            'price', 'amount', 'total', 'order', 'invoice'
        ]
        
        # Common email field names to check
        self.email_fields = [
            'body', 'content', 'text', 'message', 'html', 'plain',
            'subject', 'title', 'snippet', 'preview'
        ]
    
    async def initialize(self) -> bool:
        """Initialize the verification code extractor."""
        self.logger.info("Initializing verification code extractor...")
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass
    
    def extract_verification_code(self, message: Dict[str, Any]) -> ExtractionResult:
        """
        Extract verification code from email message using multiple methods.
        
        Args:
            message: Email message data
            
        Returns:
            ExtractionResult with best extraction result
        """
        results = []
        
        # Method 1: Primary regex patterns
        regex_result = self._extract_with_regex_patterns(message, self.primary_patterns)
        if regex_result.code:
            results.append(regex_result)
        
        # Method 2: HTML parsing
        html_result = self._extract_from_html(message)
        if html_result.code:
            results.append(html_result)
        
        # Method 3: JSON parsing
        json_result = self._extract_from_json(message)
        if json_result.code:
            results.append(json_result)
        
        # Method 4: Keyword-based search
        keyword_result = self._extract_with_keyword_search(message)
        if keyword_result.code:
            results.append(keyword_result)
        
        # Method 5: Fallback patterns
        if not results:
            fallback_result = self._extract_with_regex_patterns(message, self.fallback_patterns)
            if fallback_result.code:
                fallback_result.method = ExtractionMethod.FALLBACK
                results.append(fallback_result)
        
        # Return best result based on confidence
        if results:
            best_result = max(results, key=lambda x: x.confidence)
            self.logger.info(f"Extracted code '{best_result.code}' using {best_result.method.value} "
                           f"with confidence {best_result.confidence}")
            return best_result
        
        self.logger.warning("No verification code found in message")
        return ExtractionResult()
    
    def _extract_with_regex_patterns(self, message: Dict[str, Any], patterns: List[Tuple[str, float, str]]) -> ExtractionResult:
        """
        Extract code using regex patterns.
        
        Args:
            message: Email message data
            patterns: List of (pattern, confidence, name) tuples
            
        Returns:
            ExtractionResult with best match
        """
        best_result = ExtractionResult()
        
        # Get all text content from message
        text_content = self._extract_text_content(message)
        if not text_content:
            return best_result
        
        # Normalize text
        normalized_text = self._normalize_text(text_content)
        
        # Try each pattern
        for pattern, base_confidence, pattern_name in patterns:
            try:
                matches = re.findall(pattern, normalized_text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    if not match.isdigit():
                        continue
                    
                    # Validate code length
                    if not (3 <= len(match) <= 10):
                        continue
                    
                    # Calculate confidence based on context
                    confidence = self._calculate_context_confidence(
                        match, normalized_text, base_confidence
                    )
                    
                    if confidence > best_result.confidence:
                        best_result = ExtractionResult(
                            code=match,
                            confidence=confidence,
                            method=ExtractionMethod.REGEX_PATTERN,
                            pattern_used=pattern_name,
                            source_field="combined_text"
                        )
                        
            except re.error as e:
                self.logger.warning(f"Regex error with pattern {pattern}: {e}")
                continue
        
        return best_result   
 
    def _extract_from_html(self, message: Dict[str, Any]) -> ExtractionResult:
        """
        Extract code from HTML content with special parsing.
        
        Args:
            message: Email message data
            
        Returns:
            ExtractionResult from HTML parsing
        """
        html_fields = ['html', 'body', 'content']
        
        for field in html_fields:
            if field in message and message[field]:
                html_content = str(message[field])
                
                # Remove HTML tags but keep text
                try:
                    # Decode HTML entities
                    decoded_html = html.unescape(html_content)
                    
                    # Remove HTML tags
                    clean_text = re.sub(r'<[^>]+>', ' ', decoded_html)
                    
                    # Look for codes in clean text
                    result = self._extract_with_regex_patterns(
                        {'text': clean_text}, 
                        self.primary_patterns
                    )
                    
                    if result.code:
                        result.method = ExtractionMethod.HTML_PARSING
                        result.source_field = field
                        return result
                        
                except Exception as e:
                    self.logger.warning(f"HTML parsing error: {e}")
                    continue
        
        return ExtractionResult()
    
    def _extract_from_json(self, message: Dict[str, Any]) -> ExtractionResult:
        """
        Extract code from JSON-structured content.
        
        Args:
            message: Email message data
            
        Returns:
            ExtractionResult from JSON parsing
        """
        # Check if message itself contains structured data
        json_fields = ['data', 'payload', 'content', 'body']
        
        for field in json_fields:
            if field in message:
                try:
                    if isinstance(message[field], str):
                        # Try to parse as JSON
                        json_data = json.loads(message[field])
                    else:
                        json_data = message[field]
                    
                    # Look for verification code in JSON structure
                    code = self._find_code_in_json(json_data)
                    if code:
                        return ExtractionResult(
                            code=code,
                            confidence=0.85,
                            method=ExtractionMethod.JSON_PARSING,
                            source_field=field
                        )
                        
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return ExtractionResult()
    
    def _extract_with_keyword_search(self, message: Dict[str, Any]) -> ExtractionResult:
        """
        Extract code using keyword-based search around numbers.
        
        Args:
            message: Email message data
            
        Returns:
            ExtractionResult from keyword search
        """
        text_content = self._extract_text_content(message)
        if not text_content:
            return ExtractionResult()
        
        normalized_text = self._normalize_text(text_content)
        
        # Find all numbers
        number_matches = list(re.finditer(r'\b(\d{4,8})\b', normalized_text))
        
        best_result = ExtractionResult()
        
        for match in number_matches:
            code = match.group(1)
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(normalized_text), match.end() + 100)
            context = normalized_text[start_pos:end_pos].lower()
            
            # Count positive keywords in context
            positive_score = sum(1 for keyword in self.confidence_keywords 
                               if keyword in context)
            
            # Count negative keywords in context
            negative_score = sum(1 for keyword in self.negative_keywords 
                               if keyword in context)
            
            # Calculate confidence
            confidence = 0.3 + (positive_score * 0.1) - (negative_score * 0.15)
            confidence = max(0.0, min(1.0, confidence))
            
            if confidence > best_result.confidence:
                best_result = ExtractionResult(
                    code=code,
                    confidence=confidence,
                    method=ExtractionMethod.KEYWORD_SEARCH,
                    source_field="keyword_context"
                )
        
        return best_result   
 
    def _extract_text_content(self, message: Dict[str, Any]) -> str:
        """
        Extract all text content from message.
        
        Args:
            message: Email message data
            
        Returns:
            Combined text content
        """
        text_parts = []
        
        for field in self.email_fields:
            if field in message and message[field]:
                text_parts.append(str(message[field]))
        
        return ' '.join(text_parts)
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for better pattern matching.
        
        Args:
            text: Raw text content
            
        Returns:
            Normalized text
        """
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere
        normalized = re.sub(r'[^\w\s\d]', ' ', normalized)
        
        return normalized.strip()
    
    def _calculate_context_confidence(self, code: str, text: str, base_confidence: float) -> float:
        """
        Calculate confidence based on context around the code.
        
        Args:
            code: Extracted code
            text: Full text content
            base_confidence: Base confidence from pattern
            
        Returns:
            Adjusted confidence score
        """
        # Find code position in text
        code_pos = text.lower().find(code)
        if code_pos == -1:
            return base_confidence
        
        # Get context around code
        context_start = max(0, code_pos - 50)
        context_end = min(len(text), code_pos + len(code) + 50)
        context = text[context_start:context_end].lower()
        
        # Adjust confidence based on context
        confidence_adjustment = 0.0
        
        # Positive indicators
        for keyword in self.confidence_keywords:
            if keyword in context:
                confidence_adjustment += 0.05
        
        # Negative indicators
        for keyword in self.negative_keywords:
            if keyword in context:
                confidence_adjustment -= 0.1
        
        # Code length preference (6 digits is most common)
        if len(code) == 6:
            confidence_adjustment += 0.1
        elif len(code) == 4:
            confidence_adjustment += 0.05
        elif len(code) < 4 or len(code) > 8:
            confidence_adjustment -= 0.2
        
        final_confidence = base_confidence + confidence_adjustment
        return max(0.0, min(1.0, final_confidence))
    
    def _find_code_in_json(self, json_data: Any, depth: int = 0) -> Optional[str]:
        """
        Recursively search for verification code in JSON structure.
        
        Args:
            json_data: JSON data to search
            depth: Current recursion depth
            
        Returns:
            Found verification code or None
        """
        if depth > 5:  # Prevent infinite recursion
            return None
        
        if isinstance(json_data, dict):
            # Check for common verification code keys
            code_keys = ['code', 'verification_code', 'otp', 'token', 'pin']
            for key in code_keys:
                if key in json_data:
                    value = str(json_data[key])
                    if value.isdigit() and 4 <= len(value) <= 8:
                        return value
            
            # Recursively search values
            for value in json_data.values():
                result = self._find_code_in_json(value, depth + 1)
                if result:
                    return result
        
        elif isinstance(json_data, list):
            for item in json_data:
                result = self._find_code_in_json(item, depth + 1)
                if result:
                    return result
        
        elif isinstance(json_data, str):
            # Try to extract code from string value
            if json_data.isdigit() and 4 <= len(json_data) <= 8:
                return json_data
        
        return None    

    def extract_multiple_codes(self, message: Dict[str, Any]) -> List[ExtractionResult]:
        """
        Extract all possible verification codes from message.
        
        Args:
            message: Email message data
            
        Returns:
            List of ExtractionResult sorted by confidence
        """
        results = []
        text_content = self._extract_text_content(message)
        
        if not text_content:
            return results
        
        normalized_text = self._normalize_text(text_content)
        
        # Find all potential codes using all patterns
        all_patterns = self.primary_patterns + self.fallback_patterns
        
        for pattern, base_confidence, pattern_name in all_patterns:
            try:
                matches = re.findall(pattern, normalized_text, re.IGNORECASE)
                
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    if match.isdigit() and 3 <= len(match) <= 10:
                        confidence = self._calculate_context_confidence(
                            match, normalized_text, base_confidence
                        )
                        
                        results.append(ExtractionResult(
                            code=match,
                            confidence=confidence,
                            method=ExtractionMethod.REGEX_PATTERN,
                            pattern_used=pattern_name
                        ))
                        
            except re.error:
                continue
        
        # Remove duplicates and sort by confidence
        unique_results = {}
        for result in results:
            if result.code not in unique_results or result.confidence > unique_results[result.code].confidence:
                unique_results[result.code] = result
        
        return sorted(unique_results.values(), key=lambda x: x.confidence, reverse=True)