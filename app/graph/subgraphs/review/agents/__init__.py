"""
代码评审子图 Agents 模块

导出 Agent 类和提示词模板，供节点函数使用。
"""

from app.graph.subgraphs.review.agents.agent import (
    MistakeDetectorAgent,
    SuggestionGeneratorAgent,
    ValidationTesterAgent,
    ReviewPhase,
    ValidationStatus,
    DetectionResult,
    SuggestionResult,
    ValidationResult
)

from app.graph.subgraphs.review.agents.prompts import (
    ReviewPrompts,
    get_detection_prompt,
    get_suggestion_prompt,
    get_validation_prompt,
    get_fix_generation_prompt,
    get_improved_code_generation_prompt,
    get_quality_assessment_prompt
)

__all__ = [
    # Agent 类
    "MistakeDetectorAgent",
    "SuggestionGeneratorAgent",
    "ValidationTesterAgent",
    # 枚举类型
    "ReviewPhase",
    "ValidationStatus",
    # 数据类
    "DetectionResult",
    "SuggestionResult",
    "ValidationResult",
    # 提示词类
    "ReviewPrompts",
    # 提示词函数
    "get_detection_prompt",
    "get_suggestion_prompt",
    "get_validation_prompt",
    "get_fix_generation_prompt",
    "get_improved_code_generation_prompt",
    "get_quality_assessment_prompt",
]
