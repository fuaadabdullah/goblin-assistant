"""Error types and standardized error codes for API responses."""

from enum import Enum
from http import HTTPStatus


class ErrorType(str, Enum):
    """Standard error categories for API responses."""

    VALIDATION = "validation"
    # Request validation failed (bad input, malformed data, missing fields)

    AUTHENTICATION = "authentication"
    # Auth/authorization failed (missing/invalid credentials, permissions)

    PROVIDER = "provider"
    # LLM/AI provider error (rate limit, timeout, unavailability)

    BUSINESS_LOGIC = "business_logic"
    # Business logic error (resource not found, conflict, invalid state)

    RATE_LIMIT = "rate_limit"
    # API rate limit exceeded (client sent too many requests)

    INTERNAL = "internal"
    # Unhandled internal server error


ERROR_CODES = {
    ErrorType.VALIDATION: {
        "VALIDATION_ERROR": {
            "description": "Request validation failed",
            "status": HTTPStatus.UNPROCESSABLE_ENTITY,
            "example": "Message content must be non-empty string",
        },
        "INPUT_TOO_LARGE": {
            "description": "Request payload exceeds maximum size",
            "status": HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            "example": "Message too long (max 2000 characters)",
        },
    },
    ErrorType.AUTHENTICATION: {
        "AUTHENTICATION_REQUIRED": {
            "description": "Valid credentials required",
            "status": HTTPStatus.UNAUTHORIZED,
            "example": "Missing or invalid API key",
        },
        "INVALID_API_KEY": {
            "description": "Provided API key is invalid",
            "status": HTTPStatus.UNAUTHORIZED,
            "example": "API key not recognized",
        },
        "INSUFFICIENT_PERMISSIONS": {
            "description": "User lacks required permissions",
            "status": HTTPStatus.FORBIDDEN,
            "example": "This operation requires admin access",
        },
        "CONFIGURATION_ERROR": {
            "description": "API authentication not properly configured",
            "status": HTTPStatus.INTERNAL_SERVER_ERROR,
            "example": "API authentication not configured on server",
        },
    },
    ErrorType.PROVIDER: {
        "CHAT_PROVIDER_ERROR": {
            "description": "AI provider returned an error",
            "status": HTTPStatus.BAD_GATEWAY,
            "example": "Provider returned invalid response format",
        },
        "AUTHENTICATION_REQUIRED": {
            "description": "Authentication failed with AI provider",
            "status": HTTPStatus.UNAUTHORIZED,
            "example": "Invalid provider credentials",
        },
        "CHAT_RATE_LIMITED": {
            "description": "AI provider rate limit exceeded",
            "status": HTTPStatus.TOO_MANY_REQUESTS,
            "example": "Too many requests to provider",
        },
        "CHAT_TIMEOUT": {
            "description": "AI provider request timed out",
            "status": HTTPStatus.GATEWAY_TIMEOUT,
            "example": "Provider did not respond within timeout",
        },
        "CHAT_PROVIDER_UNAVAILABLE": {
            "description": "AI provider is unavailable",
            "status": HTTPStatus.SERVICE_UNAVAILABLE,
            "example": "Provider service temporarily unavailable",
        },
        "CHAT_BACKEND_UNAVAILABLE": {
            "description": "AI provider backend is unavailable",
            "status": HTTPStatus.SERVICE_UNAVAILABLE,
            "example": "Provider backend is not responding",
        },
    },
    ErrorType.BUSINESS_LOGIC: {
        "USER_NOT_FOUND": {
            "description": "User does not exist",
            "status": HTTPStatus.NOT_FOUND,
            "example": "User with ID 'user-123' not found",
        },
        "CONVERSATION_NOT_FOUND": {
            "description": "Conversation does not exist",
            "status": HTTPStatus.NOT_FOUND,
            "example": "Conversation not found or access denied",
        },
        "RESOURCE_NOT_FOUND": {
            "description": "Requested resource does not exist",
            "status": HTTPStatus.NOT_FOUND,
            "example": "Resource with ID 'resource-123' not found",
        },
        "INVALID_STATE": {
            "description": "Resource in invalid state for operation",
            "status": HTTPStatus.CONFLICT,
            "example": "Cannot delete a published conversation",
        },
        "DUPLICATE_RESOURCE": {
            "description": "Resource already exists",
            "status": HTTPStatus.CONFLICT,
            "example": "A conversation with this name already exists",
        },
    },
    ErrorType.RATE_LIMIT: {
        "RATE_LIMIT_EXCEEDED": {
            "description": "Client has sent too many requests",
            "status": HTTPStatus.TOO_MANY_REQUESTS,
            "example": "Rate limit exceeded. Retry after the reset window.",
        },
    },
    ErrorType.INTERNAL: {
        "INTERNAL_ERROR": {
            "description": "An internal server error occurred",
            "status": HTTPStatus.INTERNAL_SERVER_ERROR,
            "example": "Unexpected error. Check logs with request_id.",
        },
    },
}


def get_error_status_code(error_type: ErrorType, error_code: str) -> HTTPStatus:
    """Get standard HTTP status code for error type and code.

    Args:
        error_type: The error type category
        error_code: The specific error code

    Returns:
        HTTPStatus for the error, or 500 if not found
    """
    try:
        return ERROR_CODES[error_type][error_code]["status"]
    except KeyError:
        return HTTPStatus.INTERNAL_SERVER_ERROR


def get_error_description(error_type: ErrorType, error_code: str) -> str:
    """Get description for error type and code.

    Args:
        error_type: The error type category
        error_code: The specific error code

    Returns:
        Description string, or generic message if not found
    """
    try:
        return ERROR_CODES[error_type][error_code]["description"]
    except KeyError:
        return "An error occurred"
