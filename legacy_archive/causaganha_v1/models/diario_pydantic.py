from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class DiarioPydantic(BaseModel):
    """Pydantic model for a Diario, mirroring the Diario dataclass structure
    but with Pydantic validation and features.
    """

    tribunal: str
    data_diario: date = Field(alias="data")  # Alias to match dataclass field name 'data'
    url: HttpUrl
    filename: str | None = None
    hash_documento: str | None = Field(default=None, alias="hash")  # Alias for 'hash'
    pdf_path_str: str | None = Field(default=None, alias="pdf_path")
    ia_identifier: str | None = None
    status: str = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True
        # If using with ORM or needing to populate from arbitrary objects:
        # orm_mode = True # or from_attributes = True in Pydantic v2


# Example of how it might be used for creation, perhaps with fewer fields required
# class DiarioCreate(BaseModel):
#     tribunal: str
#     data_diario: date = Field(alias="data")
#     url: HttpUrl
#     filename: Optional[str] = None
#     status: str = "pending"
#
#     class Config:
#         allow_population_by_field_name = True

# Example of a model that might be returned from an API, perhaps with an ID
# class DiarioRead(DiarioPydantic):
#     id: int # Assuming some persistent ID
#
#     class Config:
#         allow_population_by_field_name = True
#         orm_mode = True # or from_attributes = True
