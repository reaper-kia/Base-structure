class DocumentNotFound(Exception):
    pass


class LLMUnavailable(Exception):
    """ИИ-компонент недоступен. Ловится в хэндлере, наружу не летит."""
