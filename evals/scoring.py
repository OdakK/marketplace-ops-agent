"""Scoring helpers: a deterministic value check and an LLM-as-judge."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

NUMBER = re.compile(r"-?\d[\d\s,.' ]*\d|-?\d")


def numbers_in(text: str) -> list[float]:
    """Extract numbers, accepting 1,234.5 / 1 234,5 / 1'234 / 12.3% styles."""
    values = []
    for raw in NUMBER.findall(text):
        s = re.sub(r"[\s' ]", "", raw)
        if "," in s and "." in s:            # 1,234.56 -> thousands comma
            s = s.replace(",", "")
        elif "," in s:                        # 1,234 (thousands) or 12,5 (decimal)
            head, _, tail = s.rpartition(",")
            s = head.replace(",", "") + ("" if len(tail) == 3 else ".") + tail
        try:
            values.append(float(s))
        except ValueError:
            continue
    return values


def values_found(answer: str, rows: list[list], tolerance: float = 0.0) -> tuple[bool, list]:
    """Check that every value of the reference rows appears in the answer.

    Numbers match within a relative tolerance, strings match case-insensitively.
    """
    numbers = numbers_in(answer)
    lowered = answer.lower()
    missing = []
    for row in rows:
        for value in row:
            if value is None:
                continue
            if isinstance(value, int | float):
                if not any(abs(n - value) <= max(tolerance * abs(value), 1e-9) for n in numbers):
                    missing.append(value)
            elif str(value).lower() not in lowered:
                missing.append(value)
    return not missing, missing


class Verdict(BaseModel):
    correct: bool = Field(description="true if the answer is factually consistent with the reference")
    reasoning: str = Field(description="one or two sentences")


JUDGE_PROMPT = """You grade answers of a data analysis agent.
You get a question, the reference result of the correct SQL query, and the agent's answer.
The answer is correct if it states the same facts as the reference result (small rounding differences
are fine, extra context is fine). It is incorrect if any key value is wrong, missing, or invented."""


async def judge(model, question: str, expected: dict, answer: str) -> dict:
    reference = json.dumps({"columns": expected["columns"], "rows": expected["rows"]}, default=str)
    grader = model.with_structured_output(Verdict)
    verdict = await grader.ainvoke([
        SystemMessage(JUDGE_PROMPT),
        HumanMessage(f"Question: {question}\n\nReference result: {reference}\n\nAgent answer: {answer}"),
    ])
    return verdict.model_dump()
