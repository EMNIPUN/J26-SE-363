"""Typed errors for Required Knowledge Identification."""


class KnowledgeIdentificationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class MissingCourseIdError(KnowledgeIdentificationError):
    def __init__(self, message: str = "course_id is required in request.input."):
        super().__init__("missing_course_id", message)


class KnowledgeLlmError(KnowledgeIdentificationError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message)


class KnowledgeValidationError(KnowledgeIdentificationError):
    def __init__(self, message: str):
        super().__init__("invalid_llm_selection", message)
