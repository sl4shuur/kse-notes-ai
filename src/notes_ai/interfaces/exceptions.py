class UnsupportedSourceError(Exception):
    def __init__(self, message, extra_info=None):
        self.extra_info = extra_info

        super().__init__(message)


class ExtractionError(Exception):
    def __init__(self, message, extra_info=None):
        self.extra_info = extra_info

        super().__init__(message)


class LLMError(Exception):
    def __init__(self, message, extra_info=None):
        self.extra_info = extra_info

        super().__init__(message)


class StorageError(Exception):
    def __init__(self, message, extra_info=None):
        self.extra_info = extra_info

        super().__init__(message)


class ConfigurationError(Exception):
    """Raised when required application configuration is unavailable."""
