
class WattsVisionError(Exception):
    """Base class for all Watts Vision errors."""
    pass


class WattsInvalidCredentialsError(WattsVisionError):
    """Exception raised for invalid credentials in Watts Vision."""
    
    def __init__(self, message: str = "Invalid credentials provided"):
        self.message = message
        super().__init__(self.message)


class WattsVisionApiStatusError(WattsVisionError):
    """Exception raised for API status errors in Watts Vision."""
    
    def __init__(self, status_code: int, message: str = "API returned an error status code"):
        self.status_code = status_code
        self.message = f"{message}: {status_code}"
        super().__init__(self.message)


class WattsVisionAuthenticationError(WattsVisionError):
    """Exception raised for authentication errors in Watts Vision."""
    
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class WattsVisionApiCodeError(WattsVisionError):
    """Exception raised for API errors in Watts Vision."""
    
    def __init__(self, code: str, key: str, value: str, message: str = "API returned an error code"):
        self.code = code
        self.message = f"{message}. Code: {code}. Key: {key}. Value: {value}."
        super().__init__(self.message)
