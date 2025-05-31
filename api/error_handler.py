"""
Robust error handling system for YouTube Subtitle Downloader.
Provides detailed error tracking and categorization for better debugging.
"""

import traceback
import sys
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum
import inspect

class ErrorCategory(Enum):
    """
    Categorizes errors to help identify the source and nature of issues.
    """
    NETWORK = "network"
    PARSING = "parsing"
    VALIDATION = "validation"
    YOUTUBE_API = "youtube_api"
    FILE_OPERATION = "file_operation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    """
    Defines error severity levels.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DetailedError:
    """
    Enhanced error object that captures comprehensive debugging information.
    """
    
    def __init__(
        self,
        error: Exception,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.error = error
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.suggestions = suggestions or []
        self.timestamp = datetime.now().isoformat()
        
        # Capture stack trace information
        self.traceback_info = self._capture_traceback()
        
        # Extract relevant context from the call stack
        self.call_context = self._extract_call_context()
        
    def _capture_traceback(self) -> Dict[str, Any]:
        """
        Captures detailed traceback information including file paths, line numbers, and function names.
        """
        tb_info = {
            "exception_type": type(self.error).__name__,
            "exception_message": str(self.error),
            "stack_trace": [],
            "formatted_traceback": traceback.format_exc()
        }
        
        # Get the current traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        if exc_traceback:
            # Extract stack frames
            stack_frames = []
            tb = exc_traceback
            
            while tb is not None:
                frame = tb.tb_frame
                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                line_number = tb.tb_lineno
                
                # Get local variables (be careful with sensitive data)
                local_vars = {}
                for var_name, var_value in frame.f_locals.items():
                    try:
                        # Only include simple types to avoid serialization issues
                        if isinstance(var_value, (str, int, float, bool, type(None))):
                            local_vars[var_name] = var_value
                        elif isinstance(var_value, (list, dict, tuple)) and len(str(var_value)) < 200:
                            local_vars[var_name] = str(var_value)[:200]
                        else:
                            local_vars[var_name] = f"<{type(var_value).__name__}>"
                    except:
                        local_vars[var_name] = "<unavailable>"
                
                stack_frames.append({
                    "filename": filename,
                    "function": function_name,
                    "line_number": line_number,
                    "local_variables": local_vars
                })
                
                tb = tb.tb_next
            
            tb_info["stack_trace"] = stack_frames
        
        return tb_info
    
    def _extract_call_context(self) -> Dict[str, Any]:
        """
        Extracts context information from the current call stack.
        """
        context = {
            "current_function": None,
            "calling_function": None,
            "module": None
        }
        
        try:
            # Get the current frame and caller information
            current_frame = inspect.currentframe()
            if current_frame and current_frame.f_back and current_frame.f_back.f_back:
                caller_frame = current_frame.f_back.f_back
                context["current_function"] = caller_frame.f_code.co_name
                context["module"] = caller_frame.f_globals.get("__name__", "unknown")
                
                if caller_frame.f_back:
                    context["calling_function"] = caller_frame.f_back.f_code.co_name
        except:
            pass  # Ignore any issues with frame inspection
        
        return context
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Converts the error object to a dictionary for serialization.
        
        Args:
            include_sensitive: Whether to include potentially sensitive debugging information
        """
        result = {
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "message": str(self.error),
            "type": type(self.error).__name__,
            "context": self.context,
            "suggestions": self.suggestions,
            "call_context": self.call_context
        }
        
        if include_sensitive:
            result["traceback"] = self.traceback_info
        else:
            # Include only sanitized traceback info
            result["traceback"] = {
                "exception_type": self.traceback_info["exception_type"],
                "exception_message": self.traceback_info["exception_message"],
                "stack_summary": [
                    {
                        "function": frame["function"],
                        "line_number": frame["line_number"],
                        "filename": frame["filename"].split("/")[-1]  # Only include filename, not full path
                    }
                    for frame in self.traceback_info.get("stack_trace", [])
                ]
            }
        
        return result

class ErrorAnalyzer:
    """
    Analyzes errors and provides categorization and suggestions.
    """
    
    @staticmethod
    def analyze_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> DetailedError:
        """
        Analyzes an error and returns a DetailedError with categorization and suggestions.
        """
        category = ErrorAnalyzer._categorize_error(error, context)
        severity = ErrorAnalyzer._assess_severity(error, category)
        suggestions = ErrorAnalyzer._generate_suggestions(error, category, context)
        
        return DetailedError(
            error=error,
            category=category,
            severity=severity,
            context=context,
            suggestions=suggestions
        )
    
    @staticmethod
    def _categorize_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorCategory:
        """
        Categorizes an error based on its type and context.
        """
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Network-related errors
        if any(keyword in error_type.lower() for keyword in ["request", "connection", "timeout", "http"]):
            return ErrorCategory.NETWORK
        
        if any(keyword in error_message for keyword in ["connection", "timeout", "network", "dns", "host"]):
            return ErrorCategory.NETWORK
        
        # YouTube API specific errors
        if any(keyword in error_message for keyword in ["youtube", "video not found", "private video", "unavailable"]):
            return ErrorCategory.YOUTUBE_API
        
        # Parsing errors
        if any(keyword in error_type.lower() for keyword in ["json", "xml", "parse", "decode"]):
            return ErrorCategory.PARSING
        
        if any(keyword in error_message for keyword in ["invalid json", "xml", "parse", "decode", "malformed"]):
            return ErrorCategory.PARSING
        
        # Validation errors
        if error_type in ["ValueError", "TypeError", "AttributeError"]:
            if context and any(keyword in str(context).lower() for keyword in ["url", "video_id", "track"]):
                return ErrorCategory.VALIDATION
        
        # Rate limiting
        if any(keyword in error_message for keyword in ["rate limit", "too many requests", "429"]):
            return ErrorCategory.RATE_LIMIT
        
        # File operation errors
        if any(keyword in error_type.lower() for keyword in ["file", "io", "permission"]):
            return ErrorCategory.FILE_OPERATION
        
        return ErrorCategory.UNKNOWN
    
    @staticmethod
    def _assess_severity(error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """
        Assesses the severity of an error.
        """
        error_message = str(error).lower()
        
        # Critical errors that completely break functionality
        if category == ErrorCategory.YOUTUBE_API and "video not found" in error_message:
            return ErrorSeverity.HIGH
        
        if category == ErrorCategory.NETWORK and any(keyword in error_message for keyword in ["timeout", "connection refused"]):
            return ErrorSeverity.HIGH
        
        # Medium severity for parsing issues
        if category == ErrorCategory.PARSING:
            return ErrorSeverity.MEDIUM
        
        # Low severity for validation issues (usually user input problems)
        if category == ErrorCategory.VALIDATION:
            return ErrorSeverity.LOW
        
        # Rate limiting is medium unless it's persistent
        if category == ErrorCategory.RATE_LIMIT:
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.MEDIUM
    
    @staticmethod
    def _generate_suggestions(error: Exception, category: ErrorCategory, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generates helpful suggestions based on the error category and context.
        """
        suggestions = []
        error_message = str(error).lower()
        
        if category == ErrorCategory.NETWORK:
            suggestions.extend([
                "Check your internet connection",
                "Verify that YouTube is accessible from your location",
                "Try again in a few moments as this might be a temporary issue"
            ])
            
            if "timeout" in error_message:
                suggestions.append("The request timed out - YouTube might be experiencing high load")
        
        elif category == ErrorCategory.YOUTUBE_API:
            if "video not found" in error_message or "private" in error_message:
                suggestions.extend([
                    "Verify the YouTube URL is correct and accessible",
                    "Check if the video is private, unlisted, or has been removed",
                    "Ensure the video has subtitles/captions available"
                ])
            else:
                suggestions.extend([
                    "The video might be region-locked or have restricted access",
                    "Try with a different YouTube video to test if the issue persists"
                ])
        
        elif category == ErrorCategory.PARSING:
            suggestions.extend([
                "This appears to be a data format issue from YouTube",
                "YouTube may have changed their page structure",
                "Try refreshing and attempting the operation again"
            ])
        
        elif category == ErrorCategory.VALIDATION:
            if context and "video_url" in context:
                suggestions.extend([
                    "Please check that you've entered a valid YouTube URL",
                    "Supported formats: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID"
                ])
        
        elif category == ErrorCategory.RATE_LIMIT:
            suggestions.extend([
                "You've made too many requests in a short time",
                "Please wait a few minutes before trying again",
                "Consider reducing the frequency of your requests"
            ])
        
        if not suggestions:
            suggestions.append("Please try the operation again or contact support if the issue persists")
        
        return suggestions

def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None, logger: Optional[logging.Logger] = None) -> DetailedError:
    """
    Main error handling function that creates a detailed error object and logs it.
    
    Args:
        error: The exception that occurred
        context: Additional context information
        logger: Logger instance for recording the error
    
    Returns:
        DetailedError object with comprehensive error information
    """
    detailed_error = ErrorAnalyzer.analyze_error(error, context)
    
    if logger:
        log_level = logging.ERROR
        if detailed_error.severity == ErrorSeverity.CRITICAL:
            log_level = logging.CRITICAL
        elif detailed_error.severity == ErrorSeverity.LOW:
            log_level = logging.WARNING
        
        logger.log(
            log_level,
            f"[{detailed_error.category.value.upper()}] {detailed_error.error}: {'; '.join(detailed_error.suggestions)}"
        )
    
    return detailed_error
