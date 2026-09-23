"""Base class for every response schema: an OpenAPI document that says what we send.

FastAPI builds response schemas in pydantic's serialization mode, where any field with a
default is left out of `required`. The API always serializes every field, so the generated
TypeScript (`frontend/src/types/api.gen.ts`) would otherwise mark them optional. Response
models inherit from `ResponseModel` to make defaulted fields required in that mode; request
models stay on `BaseModel` so their optional fields remain optional for the client.
"""

from pydantic import BaseModel, ConfigDict


class ResponseModel(BaseModel):
    """A schema the API sends; every declared field is present in the JSON."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
