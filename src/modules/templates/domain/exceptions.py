class TemplateDomainError(Exception):
    pass


class TemplateNotFoundError(TemplateDomainError):
    pass


class TemplateRulesInvalidError(TemplateDomainError):
    pass


class TemplateMissingError(TemplateDomainError):
    pass
