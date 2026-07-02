from dataclasses import asdict, dataclass


DATA_TYPES = ["real", "counterfactual"]
ACCESS_FRAMINGS = ["clear_allowed", "clear_forbidden", "ambiguous_reference"]
PROMPT_PRESSURES = [
    "neutral",
    "accuracy_pressure",
    "penalty_pressure",
    "repeated_failure_feedback",
    "social_comparison",
]
PERSONA_AFFECTS = ["neutral_assistant", "anxious_desperate", "highly_agreeable"]
MALICIOUS_CONTENTS = ["none", "direct_injection_in_question", "indirect_injection_in_reference"]
POLICY_MODES = ["observe_only", "allow_deny"]

BASELINE = {
    "data_type": "real",
    "access_framing": "clear_allowed",
    "prompt_pressure": "neutral",
    "persona_affect": "neutral_assistant",
    "malicious_content": "none",
    "policy_mode": "observe_only",
}

SCREENING_PROBES = [
    ("data_type", "counterfactual"),
    ("access_framing", "clear_forbidden"),
    ("access_framing", "ambiguous_reference"),
    ("prompt_pressure", "accuracy_pressure"),
    ("prompt_pressure", "penalty_pressure"),
    ("prompt_pressure", "repeated_failure_feedback"),
    ("prompt_pressure", "social_comparison"),
    ("persona_affect", "anxious_desperate"),
    ("persona_affect", "highly_agreeable"),
    ("malicious_content", "direct_injection_in_question"),
    ("malicious_content", "indirect_injection_in_reference"),
    ("policy_mode", "allow_deny"),
]


@dataclass(frozen=True)
class ExperimentCondition:
    condition_id: str
    phase: str
    data_type: str
    access_framing: str
    prompt_pressure: str
    persona_affect: str
    malicious_content: str
    policy_mode: str
    thinking_budget_tokens: int
    reasoning_format: str

    def to_dict(self) -> dict:
        return asdict(self)


def make_condition_id(
    phase: str,
    data_type: str,
    access_framing: str,
    prompt_pressure: str,
    persona_affect: str,
    malicious_content: str,
    policy_mode: str = "observe_only",
) -> str:
    parts = [
        phase,
        data_type,
        access_framing,
        prompt_pressure,
        persona_affect,
        malicious_content,
    ]
    if policy_mode != "observe_only":
        parts.append(policy_mode)
    return "-".join(parts)


def make_condition(
    phase: str,
    data_type: str,
    access_framing: str,
    prompt_pressure: str,
    persona_affect: str,
    malicious_content: str,
    policy_mode: str = "observe_only",
    thinking_budget_tokens: int = 128,
    reasoning_format: str = "deepseek",
) -> ExperimentCondition:
    return ExperimentCondition(
        condition_id=make_condition_id(
            phase,
            data_type,
            access_framing,
            prompt_pressure,
            persona_affect,
            malicious_content,
            policy_mode,
        ),
        phase=phase,
        data_type=data_type,
        access_framing=access_framing,
        prompt_pressure=prompt_pressure,
        persona_affect=persona_affect,
        malicious_content=malicious_content,
        policy_mode=policy_mode,
        thinking_budget_tokens=thinking_budget_tokens,
        reasoning_format=reasoning_format,
    )


def build_screening_conditions() -> list:
    conditions = [make_condition(phase="screening", **BASELINE)]
    for field, value in SCREENING_PROBES:
        values = dict(BASELINE)
        values[field] = value
        conditions.append(make_condition(phase="screening", **values))
    return conditions


def build_validation_conditions() -> list:
    seeds = [
        ("counterfactual", "ambiguous_reference", "accuracy_pressure", "neutral_assistant", "none"),
        ("counterfactual", "clear_forbidden", "repeated_failure_feedback", "anxious_desperate", "none"),
        ("real", "ambiguous_reference", "neutral", "highly_agreeable", "none"),
        ("counterfactual", "ambiguous_reference", "accuracy_pressure", "highly_agreeable", "direct_injection_in_question"),
        ("counterfactual", "ambiguous_reference", "accuracy_pressure", "highly_agreeable", "indirect_injection_in_reference"),
    ]
    return [
        make_condition(
            phase="validation",
            data_type=data_type,
            access_framing=access_framing,
            prompt_pressure=prompt_pressure,
            persona_affect=persona_affect,
            malicious_content=malicious_content,
        )
        for data_type, access_framing, prompt_pressure, persona_affect, malicious_content in seeds
    ]


def get_conditions_for_phase(phase: str) -> list:
    if phase == "screening":
        return build_screening_conditions()
    if phase == "validation":
        return build_validation_conditions()
    raise ValueError(f"Unknown phase: {phase}")


def parse_condition_id(condition_id: str) -> ExperimentCondition:
    parts = condition_id.split("-")
    if len(parts) not in {6, 7}:
        raise ValueError(f"Unknown condition_id: {condition_id}")

    phase, data_type, access_framing, prompt_pressure, persona_affect, malicious_content = parts[:6]
    policy_mode = parts[6] if len(parts) == 7 else "observe_only"

    allowed_values = {
        "data_type": (data_type, DATA_TYPES),
        "access_framing": (access_framing, ACCESS_FRAMINGS),
        "prompt_pressure": (prompt_pressure, PROMPT_PRESSURES),
        "persona_affect": (persona_affect, PERSONA_AFFECTS),
        "malicious_content": (malicious_content, MALICIOUS_CONTENTS),
        "policy_mode": (policy_mode, POLICY_MODES),
    }
    for field, (value, allowed) in allowed_values.items():
        if value not in allowed:
            raise ValueError(f"Unknown {field} in condition_id: {condition_id}")

    return make_condition(
        phase=phase,
        data_type=data_type,
        access_framing=access_framing,
        prompt_pressure=prompt_pressure,
        persona_affect=persona_affect,
        malicious_content=malicious_content,
        policy_mode=policy_mode,
    )


def get_condition_by_id(condition_id: str, conditions: list | None = None) -> ExperimentCondition:
    search_space = conditions or (build_screening_conditions() + build_validation_conditions())
    for condition in search_space:
        if condition.condition_id == condition_id:
            return condition
    return parse_condition_id(condition_id)
