"""Custom exceptions for Watts Vision API errors."""


class WattsVisionError(Exception):
    """Base class for all Watts Vision errors."""


class WattsInvalidCredentialsError(WattsVisionError):
    """Exception raised for invalid credentials in Watts Vision during authentication."""

    def __init__(self, message: str = "Invalid credentials provided"):
        """Initializes WattsInvalidCredentialsError."""

        self.message = message
        super().__init__(self.message)


class WattsVisionApiStatusError(WattsVisionError):
    """Exception raised for API status errors in Watts Vision."""

    def __init__(
        self, status_code: int, message: str = "API returned an error status code"
    ):
        """Initializes WattsVisionApiStatusError."""

        self.status_code = status_code
        self.message = f"{message}: {status_code}"
        super().__init__(self.message)


class WattsVisionAuthenticationError(WattsVisionError):
    """Exception raised for authentication errors in Watts Vision during API usage (expired tokens)."""

    def __init__(self, message: str = "Authentication failed"):
        """Initializes WattsVisionAuthenticationError."""

        self.message = message
        super().__init__(self.message)


class WattsVisionApiCodeError(WattsVisionError):
    """Exception raised for API errors in Watts Vision."""

    def __init__(
        self,
        code: str,
        key: str,
        value: str,
        message: str = "API returned an error code",
    ):
        """Initializes WattsVisionApiCodeError."""

        self.code = code
        self.message = f"{message}. Code: {code}. Key: {key}. Value: {value}."
        super().__init__(self.message)
