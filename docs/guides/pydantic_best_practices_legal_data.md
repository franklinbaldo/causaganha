# Pydantic Best Practices for Judicial Data

This document outlines best practices for using Pydantic models in the CausaGanha project, particularly when dealing with judicial and legal data.

## 1. Core Principles

- **Clarity and Explicitness**: Models should clearly define the expected data structure. Use descriptive field names.
- **Strict Validation**: Leverage Pydantic's validation capabilities to ensure data integrity as early as possible.
- **Immutability where appropriate**: Consider using frozen models (`class Config: frozen = True`) for data that should not change after creation, though this may not always be suitable for ORM-like objects.

## 2. Field Types and Validation

- **Use Specific Types**:
    - `HttpUrl` for URLs.
    - `EmailStr` for email addresses.
    - `datetime.date` for dates, `datetime.datetime` for timestamps.
    - `Enum` (from Python's `enum` module) for fields with a controlled vocabulary (e.g., `tipo_decisao`, `status`, `resultado`).
    - `List[SubModel]` or `Dict[str, SubModel]` for nested structured data.
- **Custom Validators**:
    - Use `@validator` (Pydantic v1) or `@field_validator` (Pydantic v2) for complex validation rules not covered by standard types.
    - Examples for legal data:
        - Validating CNJ (Conselho Nacional de Justiça) process number format.
        - Validating OAB (Ordem dos Advogados do Brasil) number format.
        - Ensuring date consistency (e.g., `data_decisao` is not in the future).
- **Constrained Types**:
    - `constr` for strings with min/max length, regex patterns.
    - `conint`, `confloat`, `conlist` for constrained numbers and lists.
- **Optional Fields and Defaults**:
    - Clearly distinguish between `Optional[X]` (can be `None`) and fields with default values (`field_name: X = default_value` or `Field(default=...)`).
    - Use `Field(default_factory=...)` for mutable default types (e.g., `list`, `dict`).

## 3. Model Configuration (`class Config`)

- **`allow_population_by_field_name` (V1) / `populate_by_name` (V2)**: Useful when field names in input data differ from model attribute names (e.g., using `alias`). Set to `True`.
- **`from_attributes` (V2) / `orm_mode` (V1)**: Set to `True` if creating Pydantic models from ORM objects or other arbitrary class instances.
- **`extra` behavior**:
    - `'ignore'`: Silently ignore extra fields in input data.
    - `'forbid'`: Raise an error if extra fields are present (stricter, often better for APIs).
    - `'allow'`: Allow extra fields and include them in the model instance (use with caution).
- **JSON Encoders (`json_encoders`)**:
    - Provide custom serializers for types not natively handled by `json.dumps` (e.g., `pathlib.Path: str`, `datetime.timedelta`).
    - Consider using `orjson` for improved JSON parsing/serialization performance if needed, by setting `json_loads` and `json_dumps` in `Config`.

## 4. Aliases

- Use `Field(alias="external_field_name")` to map Pythonic attribute names to differently named fields in external data sources (e.g., database columns, API responses).
- Remember to set `allow_population_by_field_name = True` (or `populate_by_name = True` in V2) in `Config`.

## 5. Nested Models

- Define separate Pydantic models for nested data structures to maintain clarity and reusability.
- Example: An `ExtractedDecision` model might contain a `List[PartyInfo]` where `PartyInfo` is another Pydantic model.

## 6. Serialization

- Use `.model_dump()` (V2) or `.dict()` (V1) for converting models to dictionaries.
    - `exclude_unset=True`: Useful for PATCH operations or when you only want to serialize fields that were explicitly set.
    - `exclude_none=True`: Omits fields that have a `None` value.
    - `by_alias=True`: Serializes using field aliases if defined.
- Use `.model_dump_json()` (V2) or `.json()` (V1) for direct JSON string output.

## 7. Model Inheritance

- Use standard Python class inheritance to create variations of models (e.g., `ModelCreate`, `ModelRead`, `ModelUpdate` inheriting from a `ModelBase`). This promotes DRY (Don't Repeat Yourself).

## 8. Forward References and Postponed Annotations

- Use `from __future__ import annotations` (Python 3.7+) to simplify type hints, especially for self-referencing models or circular dependencies between models.
- Alternatively, use string literals for type hints (e.g., `field: 'MyOtherModel'`) and call `MyModel.model_rebuild()` (V2) or `MyModel.update_forward_refs()` (V1) after all relevant models are defined.

## 9. Judicial Data Specifics

- **Process Numbers (CNJ)**: Consider a custom type or validator for CNJ format `NNNNNNN-DD.YYYY.J.TR.OOOO`.
- **Legal Terms**: For fields representing specific legal terms or codes (e.g., class codes, movement codes), use `Enum` for consistency and to limit allowed values.
- **Anonymization/PII**: If models handle PII, ensure fields are clearly marked or consider separate models for anonymized vs. non-anonymized data. Pydantic can be used to strip PII during serialization by selectively excluding fields.

## 10. Versioning
- As data structures evolve, consider versioning your Pydantic models, especially if they are used in APIs or persistent storage. This can be done via module versioning, namespaces, or specific fields in the model (e.g., `model_version: str = "1.0.0"`).

By following these practices, we can ensure that our Pydantic models are robust, maintainable, and effectively validate the complex data structures found in legal documents.
