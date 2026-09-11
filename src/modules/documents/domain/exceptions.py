class DocumentNotFound(Exception):
    pass


class LLMUnavailable(Exception):
    """ИИ-компонент недоступен. Ловится в хэндлере, наружу не летит."""


class DocTypeNotFound(Exception):
    def __init__(self, doc_type: str) -> None:
        self.doc_type = doc_type
        super().__init__(f"Неизвестный тип документа: {doc_type}")
