"""Custom exceptions for CFS operations."""


class CFSError(Exception):
    """Base exception for CFS operations."""

    pass


class CFSNotFoundError(CFSError):
    """Raised when CFS structure is not found."""

    def __init__(self, message: str = "CFS structure not found. Run 'cfs init' first."):
        self.message = message
        super().__init__(self.message)


class InvalidCategoryError(CFSError):
    """Raised when an invalid category is specified."""

    def __init__(self, category: str, valid_categories: set[str]):
        self.category = category
        self.valid_categories = valid_categories
        message = (
            f"Invalid category: {category}. "
            f"Valid categories are: {', '.join(sorted(valid_categories))}"
        )
        super().__init__(message)


class DocumentNotFoundError(CFSError):
    """Raised when a document is not found."""

    def __init__(self, doc_id: int, category: str):
        self.doc_id = doc_id
        self.category = category
        message = f"Document with ID {doc_id} not found in {category} category"
        super().__init__(message)


class InvalidDocumentIDError(CFSError):
    """Raised when an invalid document ID is provided."""

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        message = f"Invalid document ID: {doc_id}. Expected a numeric ID or filename."
        super().__init__(message)


class DocumentOperationError(CFSError):
    """Raised when a document operation fails."""

    def __init__(self, operation: str, message: str):
        self.operation = operation
        self.message = message
        super().__init__(f"Failed to {operation}: {message}")
