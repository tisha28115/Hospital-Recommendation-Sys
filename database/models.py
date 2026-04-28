from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SeverityLabel = Literal["mild", "moderate", "severe", "emergency"]


class DoctorRecommendation(BaseModel):
    doctor_name: str
    specialization: str
    available_slots: list[str] = Field(default_factory=list, description="ISO date+time strings")


class AppointmentConfirmation(BaseModel):
    patient_name: str
    doctor_name: str
    date: str
    time: str
    status: Literal["confirmed", "cancelled", "rescheduled_needed"] = "confirmed"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str
    data: dict[str, Any] | None = None
    language: str | None = None
