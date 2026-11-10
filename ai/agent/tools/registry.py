"""오케스트레이터가 쓰는 도구 등록·실행.

- 도구 하나 = 이름 + 설명 + 입력 스키마(JSON Schema 일부) + 실행 함수 + 의도(intent)
- `openai_specs()` → LLMClient.chat(tools=...)에 그대로 넣는 형식
- `run()` 은 예외를 밖으로 던지지 않고 {"error": ...}를 돌려준다 → 모델이 읽고 사용자에게 다시 묻거나 고칠 수 있게
- 숫자·병원 정보는 도구 결과에서만 나온다 (LLM이 만들지 않음, docs/agent-spec.md 공통 규칙)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

JSON = dict[str, Any]


@dataclass
class ToolContext:
    """대화마다 서버가 채우는 값. patient_id는 LLM이 바꿀 수 없다.
    residency만 record_residency 도구로 사용자가 말한 값을 기록할 수 있다."""

    patient_id: str | None = None
    language: str = "en"
    # 국내 거주 여부: "short_term"(단기 방문) | "resident"(외국인등록·거소신고·건보 가입) | None(아직 모름)
    # resident는 상담 예약 연결 불가 (의료법 제27조 제3항 제2호, 시행규칙 제19조의2)
    residency: str | None = None
    last_user_text: str = ""  # 이번 턴 사용자 메시지 원문 (record_residency가 실제 발화인지 확인하는 데 씀)


Handler = Callable[[JSON, ToolContext], JSON]


@dataclass
class Tool:
    name: str
    description: str
    parameters: JSON
    handler: Handler
    intent: str  # 병원찾기 / 정보질문 / 가격 / 예약 / 예약상태 / 사후문의 / 진료과안내
    fake: bool = True  # 아직 가짜 응답이면 True (실제 DB·API 연결 후 False)

    def spec(self) -> JSON:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.parameters},
        }


class ToolError(Exception):
    pass


_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}


def validate(schema: JSON, args: JSON) -> list[str]:
    """필요한 만큼만 검사: required, type, enum, array items의 type·enum, 정의 안 된 키."""
    problems: list[str] = []
    props: JSON = schema.get("properties", {})
    for key in schema.get("required", []):
        if args.get(key) in (None, "", []):
            problems.append(f"'{key}' 값이 필요합니다")
    for key, value in args.items():
        if key not in props:
            problems.append(f"알 수 없는 입력 '{key}'")
            continue
        p = props[key]
        expected = _TYPES.get(p.get("type", ""))
        if expected and value is not None:
            if isinstance(value, bool) and p.get("type") in ("integer", "number"):
                problems.append(f"'{key}'는 {p['type']}이어야 합니다")
                continue
            if not isinstance(value, expected):
                problems.append(f"'{key}'는 {p['type']}이어야 합니다")
                continue
        if "enum" in p and value not in p["enum"]:
            problems.append(f"'{key}'는 {p['enum']} 중 하나여야 합니다")
        if p.get("type") == "array" and isinstance(value, list):
            item = p.get("items", {})
            for v in value:
                if "enum" in item and v not in item["enum"]:
                    problems.append(f"'{key}'의 값 '{v}'는 {item['enum']} 중 하나여야 합니다")
                elif item.get("type") and not isinstance(v, _TYPES[item["type"]]):
                    problems.append(f"'{key}'의 항목은 {item['type']}이어야 합니다")
        if p.get("type") == "integer" and isinstance(value, int):
            if "minimum" in p and value < p["minimum"] or "maximum" in p and value > p["maximum"]:
                problems.append(f"'{key}'는 {p.get('minimum')}~{p.get('maximum')} 범위여야 합니다")
    return problems


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> Tool:
        if tool.name in self.tools:
            raise ValueError(f"도구 이름 중복: {tool.name}")
        self.tools[tool.name] = tool
        return tool

    def openai_specs(self, names: list[str] | None = None) -> list[JSON]:
        chosen = names or list(self.tools)
        return [self.tools[n].spec() for n in chosen]

    def run(self, name: str, args: JSON | None, ctx: ToolContext) -> JSON:
        tool = self.tools.get(name)
        if tool is None:
            return {"error": f"없는 도구: {name}", "available": list(self.tools)}
        args = args or {}
        problems = validate(tool.parameters, args)
        if problems:
            return {"error": "입력 확인 필요", "problems": problems}
        try:
            result = tool.handler(args, ctx)
        except ToolError as e:
            return {"error": str(e)}
        if tool.fake:
            result = {**result, "_demo": True}  # 가짜 응답 표시 (시연·테스트 구분용)
        return result
