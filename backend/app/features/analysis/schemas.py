from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Rule(BaseModel):
    id: str
    title: str
    document: str
    section: str
    url: str
    rationale: str


class EvidenceFrame(BaseModel):
    timestamp_sec: float = Field(ge=0)
    image_base64: str = Field(min_length=1)


class Violation(BaseModel):
    type: str
    timecode_sec: float = Field(ge=0)
    description: str
    evidence_frames: list[EvidenceFrame] = Field(min_length=1, max_length=3)
    rule: Rule


class AnalysisResult(BaseModel):
    verdict: Literal["no_violation", "violation"]
    violations: list[Violation]
    model: str
    sampled_frames: int = Field(ge=1)
    duration_sec: float = Field(gt=0)
    limitations: str

    @model_validator(mode="after")
    def consistent_verdict(self):
        if (self.verdict == "violation") != bool(self.violations):
            raise ValueError("Verdict must match the violations list")
        return self


class Job(BaseModel):
    job_id: str
    status: Literal["processing", "done", "failed"] = "processing"
    progress: int = Field(default=0, ge=0, le=100)
    stage: str = "accepted"
    elapsed_sec: float = 0
    error: str | None = None
    verdict: Literal["no_violation", "violation"] | None = None
    violations: list[Violation] = Field(default_factory=list)
    model: str | None = None
    sampled_frames: int | None = None
    duration_sec: float | None = None
    limitations: str | None = None


class ModelEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    frame_index: int = Field(ge=0)
    rule_id: Literal[
        "personal_items",
        "cash_concealment",
        "unattended_cash",
        "cash_not_secured",
        "cashier_leaves_client",
    ]
    observation: str = Field(min_length=10, max_length=800)


class ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[ModelEvent] = Field(max_length=8)


class EvidenceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observation: str = Field(min_length=10, max_length=800)
    cashier_left_workstation: bool
    customer_still_at_counter: bool
    banknotes_on_counter: bool
    previous_customer_departed: bool
    cashier_personal_item: bool
    banknotes_into_personal_storage: bool

    def supports(self, rule_id: str) -> bool:
        required = {
            "personal_items": (self.cashier_personal_item,),
            "cash_concealment": (self.banknotes_into_personal_storage,),
            "unattended_cash": (self.banknotes_on_counter, self.cashier_left_workstation),
            "cash_not_secured": (self.banknotes_on_counter, self.previous_customer_departed),
            "cashier_leaves_client": (
                self.cashier_left_workstation, self.customer_still_at_counter,
            ),
        }
        return all(required[rule_id])
