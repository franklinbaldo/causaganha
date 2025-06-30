# Pydantic Best Practices for Judicial Data

This document outlines best practices for using Pydantic models within the CausaGanha project, particularly for data validation and serialization of judicial data.

## 1. Model Definition

-   **Be Specific with Types**: Use precise types (e.g., `datetime.date`, `HttpUrl`, `PositiveInt`). For constrained strings (like `numero_processo` CNJ format), consider `Annotated` types with custom validation or specific `PatternStr`.
    ```python
    from pydantic import BaseModel, Field, HttpUrl
    from typing import Annotated
    from datetime import date

    # Example for numero_processo (adjust regex as needed)
    CnjProcessNumber = Annotated[str, Field(pattern=r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")]

    class MyModel(BaseModel):
        publication_date: date
        document_url: HttpUrl
        process_number: Optional[CnjProcessNumber] = None
    ```
-   **Use `Optional` for Non-Required Fields**: Clearly distinguish between fields that must be present and those that might be missing.
-   **`default_factory` for Mutable Defaults**: For fields like `list` or `dict` that should have a default empty value, use `default_factory=list` or `default_factory=dict` to avoid shared mutable defaults.
    ```python
    from pydantic import BaseModel, Field
    from typing import List, Dict

    class Example(BaseModel):
        tags: List[str] = Field(default_factory=list)
        details: Dict[str, str] = Field(default_factory=dict)
    ```
-   **Aliases for External Data**: If the source data (e.g., LLM output, external API) uses different field names (e.g., `process_ID` vs `process_id`), use `Field(alias='...')` to map them. Set `populate_by_name=True` in model `Config` to allow using either name on input.
    ```python
    class Item(BaseModel):
        item_id: int = Field(alias='itemID')

        class Config:
            populate_by_name = True

    # Allows Item(itemID=1) or Item(item_id=1)
    ```

## 2. Validation

-   **Field Validators (`@field_validator`)**: Use for complex validation logic specific to one field. They can run `before` or `after` Pydantic's internal type conversion and validation.
    ```python
    from pydantic import BaseModel, field_validator, ValidationError

    class Event(BaseModel):
        start_date: date
        end_date: date

        @field_validator('end_date')
        @classmethod
        def end_date_after_start_date(cls, v: date, values: dict) -> date:
            # For Pydantic v2, use model_validator for cross-field validation.
            # This example is more suited for model_validator.
            # For a simple field validator:
            # if v.year < 2000:
            #    raise ValueError("Year must be 2000 or later")
            # return v
            pass # Placeholder, see model_validator
    ```
-   **Model Validators (`@model_validator`)**: Use for validation logic that depends on multiple fields (cross-field validation).
    ```python
    from pydantic import BaseModel, model_validator, ValidationError
    from datetime import date

    class Event(BaseModel):
        start_date: date
        end_date: date

        @model_validator(mode='after')
        def check_dates(self) -> 'Event':
            if self.start_date and self.end_date and self.end_date < self.start_date:
                raise ValueError("end_date must be after start_date")
            return self
    ```
-   **Strict Mode**: For stricter type checking (e.g., no automatic coercion from `int` to `str`), explore `StrictStr`, `StrictInt`, etc., or configure strictness in `Config`.
-   **Custom Data Types**: For highly specific formats (e.g., OAB numbers), consider creating custom Pydantic-compatible types by implementing `__get_pydantic_core_schema__`.

## 3. Serialization & Parsing

-   **Serialization (`.model_dump()`, `.model_dump_json()`):**
    -   Use `exclude_none=True` if you want to omit fields that are `None`.
    -   Use `by_alias=True` if you want the output keys to use field aliases.
    -   `mode='json'` in `model_dump()` can be useful if you need to further process Python objects that are JSON-encodable (like `date` -> `str`).
-   **Parsing (`MyModel.model_validate(data)`, `MyModel.model_validate_json(json_data)`):**
    -   These are the Pydantic v2 methods (replacing `parse_obj`, `parse_raw` from v1).
    -   Handle `ValidationError` exceptions gracefully to provide feedback on invalid data.
    ```python
    try:
        item = MyModel.model_validate(raw_data_dict)
    except ValidationError as e:
        print(f"Data validation error: {e.errors()}")
    ```

## 4. Model Organization & Reusability

-   **Nested Models**: Use nested Pydantic models to represent complex object structures (e.g., an `ExtractionResult` containing a list of `Decision` models).
-   **Shared Models**: Define common entities (like `Advogado`, `Parte`) as their own Pydantic models and reuse them across different data structures.
-   **Configuration (`Config` class):**
    -   `from_attributes = True` (Pydantic v2, formerly `orm_mode`): Allows creating models from ORM objects or other objects with attributes.
    -   `extra = 'ignore'` or `'forbid'`: Controls behavior when unexpected fields are present in input data. `'ignore'` is often safer for external data, `'forbid'` is stricter.
    -   `populate_by_name = True`: Allows initialization using field names OR aliases.
    -   `arbitrary_types_allowed = True`: Useful for types like `pathlib.Path` if not natively supported or if custom validation is tricky.

## 5. Judicial Data Specifics

-   **Dates**: Always use `datetime.date` or `datetime.datetime`. Ensure consistent timezone handling for `datetime` (Pydantic v2 has better awareness).
-   **Normalization**: Consider adding validators to normalize data on input (e.g., stripping whitespace, uppercasing certain fields like `tribunal` codes).
    ```python
    class CaseInfo(BaseModel):
        case_id: str

        @field_validator('case_id', mode='before')
        @classmethod
        def normalize_case_id(cls, v: str) -> str:
            if isinstance(v, str):
                return v.strip().upper()
            return v
    ```
-   **Handling Large Text/Resumos**: For `resumo` fields, consider `Field(max_length=...)` if a strict limit from the LLM is enforced or desired.
-   **Enum for Controlled Vocabularies**: For fields like `tipo_decisao` or `resultado` where there's a fixed set of valid values, use Python's `Enum` type. Pydantic integrates well with Enums.
    ```python
    from enum import Enum
    class ResultadoEnum(str, Enum): # Inherit from str for easy serialization
        PROCEDENTE = "procedente"
        IMPROCEDENTE = "improcedente"
        PARCIALMENTE_PROCEDENTE = "parcialmente_procedente"
        # ... other values

    class DecisionModel(BaseModel):
        resultado: ResultadoEnum
    ```

## 6. Evolution & Versioning (Advanced)

-   If models change frequently, consider strategies for versioning your Pydantic models or handling data conforming to older schemas, especially if data is persisted long-term. This is a more advanced topic beyond basic best practices.

By following these practices, we can ensure that data related to judicial processes is handled consistently, validated robustly, and is easy to work with throughout the CausaGanha application.
