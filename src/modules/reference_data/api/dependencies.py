from functools import lru_cache

from src.modules.reference_data.application.ports import ReferenceDataSource
from src.modules.reference_data.infra.null_source import NullReferenceSource


@lru_cache
def get_reference_source() -> ReferenceDataSource:
    return NullReferenceSource.from_settings()
