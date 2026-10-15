from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

class AdvisoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    source_name: str = Field(min_length=1, max_length=100)
    source_record_id: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=300)
    original_text: str = Field(min_length=1, max_length=50000)
    region: str = Field(min_length=1, max_length=200)
    issued_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    source_url: HttpUrl | None = None
    is_demo: bool = True

    @model_validator(mode="after")
    def validate_timestamps(self):
        for name in ("issued_at", "valid_from", "valid_until"):
            value = getattr(self, name)
            if value is not None:
                if value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError(f"{name} must include a timezone")
                setattr(self, name, value.astimezone(timezone.utc))
        if self.valid_from is not None and self.valid_until is not None:
            if self.valid_until <= self.valid_from:
                raise ValueError("valid_until must be later than valid_from")
        return self

class AdvisoryRead(BaseModel):
    id: int
    source_name: str
    source_record_id: str
    title: str | None
    original_text: str
    region: str
    issued_at: datetime | None
    valid_from: datetime | None
    valid_until: datetime | None
    retrieved_at: datetime
    source_url: str | None
    is_demo: bool
    is_current: bool
    current_reason: str | None = None
    source_verified: bool = False
    model_config = ConfigDict(from_attributes=True)

class SourceStatusRead(BaseModel):
    source_name: str
    status: str
    freshness: str | None = None
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    notes: str | None
    is_demo: bool
    model_config = ConfigDict(from_attributes=True)
