"""
代码评审子图 Agent 提示词模板

本模块定义代码评审子图中各个 Agent 专用的系统提示词，包括：
- Mistake Detector Agent: 问题检测提示词
- Suggestion Generator Agent: 建议生成提示词
- Validation Tester Agent: 验证测试提示词
"""

from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any


class ReviewPrompts:
    """代码评审子图提示词模板集合"""

    @staticmethod
    def get_detection_prompt() -> ChatPromptTemplate:
        """
        问题检测提示词

        用于全面扫描代码，识别逻辑错误、边界条件问题、性能瓶颈和安全隐患。
        """
        return ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的代码审查专家。你的任务是全面分析给定的代码，识别所有潜在问题。

请从以下维度进行检测：
1. **逻辑错误**: 算法逻辑错误、条件判断错误、循环逻辑问题
2. **边界条件**: 空输入、极端值、边界情况处理
3. **性能问题**: 时间复杂度过高、不必要的重复计算、内存浪费
4. **安全隐患**: 输入验证缺失、潜在的注入风险、资源泄漏
5. **可读性**: 命名不清晰、缺少注释、代码结构混乱
6. **可维护性**: 代码重复、耦合度高、缺少错误处理

对于每个发现的问题，请提供：
- 问题类型和严重程度
- 问题所在的具体行号
- 详细的问题描述
- 具体的修复建议
- 示例修复代码（如果适用）

请确保分析全面、准确且具有建设性。"""),
            ("human", """请分析以下代码的问题：

编程语言: {language}
优化级别: {optimization_level}

代码：
```{language}
{code}
```

请提供详细的问题检测报告。""")
        ])

    @staticmethod
    def get_suggestion_prompt() -> ChatPromptTemplate:
        """
        建议生成提示词

        用于根据检测到的问题生成具体的优化建议和改进代码。
        """
        return ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的代码优化专家。你的任务是根据检测到的代码问题，生成具体的优化建议和改进代码。

请为每个问题提供：
1. **改进类型**: 明确说明这是什么类型的改进（性能优化、安全加固、可读性提升等）
2. **原始代码**: 指出需要改进的具体代码片段
3. **改进后代码**: 提供完整的改进代码
4. **详细说明**: 解释为什么这样改进，以及改进带来的好处
5. **影响评估**: 评估改进的影响程度（0-10分）

优化原则：
- 保持代码的功能不变
- 优先修复高严重性问题
- 提供可直接应用的代码
- 考虑代码的可读性和可维护性
- 遵循最佳实践和编码规范

请确保建议具体、可行且有价值。"""),
            ("human", """请为以下代码问题生成优化建议：

原始代码：
```{language}
{code}
```

检测到的问题：
{issues}

优化级别: {optimization_level}

请生成详细的优化建议和改进代码。""")
        ])

    @staticmethod
    def get_validation_prompt() -> ChatPromptTemplate:
        """
        验证测试提示词

        用于验证改进代码的正确性和质量提升效果。
        """
        return ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的代码测试专家。你的任务是验证改进代码的正确性和质量。

请从以下维度进行验证：
1. **功能正确性**: 改进后的代码是否保持了原有功能
2. **问题修复**: 检测到的问题是否得到有效修复
3. **代码质量**: 代码质量是否有实质性提升
4. **性能改进**: 性能是否得到优化（如果适用）
5. **潜在风险**: 改进是否引入了新的问题

验证方法：
- 对比原始代码和改进代码
- 分析改进的合理性和有效性
- 评估代码质量指标
- 识别潜在的新问题

请提供详细的验证报告和质量评分（0-10分）。"""),
            ("human", """请验证以下代码改进：

原始代码：
```{language}
{original_code}
```

改进代码：
```{language}
{improved_code}
```

应用的优化建议：
{suggestions}

请提供详细的验证报告。""")
        ])

    @staticmethod
    def get_fix_generation_prompt() -> str:
        """
        修复代码生成提示词模板

        Returns:
            修复代码生成的提示词字符串模板
        """
        return """请为以下代码问题提供修复方案：

问题类型: {issue_type}
问题描述: {description}
修复建议: {suggestion}

原始代码：
```{language}
{code_snippet}
```

请提供改进后的代码（只返回代码，不要其他说明）：
"""

    @staticmethod
    def get_improved_code_generation_prompt() -> str:
        """
        改进代码生成提示词模板

        Returns:
            改进代码生成的提示词字符串模板
        """
        return """请根据以下优化建议，生成改进后的完整代码：

原始代码：
```{language}
{original_code}
```

优化建议：
{improvements_desc}

优化级别: {optimization_level}

请提供完整的改进代码（保持原有功能，应用所有优化建议）：
"""

    @staticmethod
    def get_quality_assessment_prompt() -> str:
        """
        质量评估提示词模板

        Returns:
            质量评估的提示词字符串模板
        """
        return """请评估以下代码的质量（0-10分）：

```{language}
{code}
```

请从以下维度评分：
1. 可读性 (readability)
2. 可维护性 (maintainability)
3. 性能 (performance)
4. 安全性 (security)
5. 最佳实践 (best_practices)

请以 JSON 格式返回评分。
"""


# 便捷函数，用于获取提示词模板

def get_detection_prompt() -> ChatPromptTemplate:
    """获取问题检测提示词"""
    return ReviewPrompts.get_detection_prompt()


def get_suggestion_prompt() -> ChatPromptTemplate:
    """获取建议生成提示词"""
    return ReviewPrompts.get_suggestion_prompt()


def get_validation_prompt() -> ChatPromptTemplate:
    """获取验证测试提示词"""
    return ReviewPrompts.get_validation_prompt()


def get_fix_generation_prompt() -> str:
    """获取修复代码生成提示词"""
    return ReviewPrompts.get_fix_generation_prompt()


def get_improved_code_generation_prompt() -> str:
    """获取改进代码生成提示词"""
    return ReviewPrompts.get_improved_code_generation_prompt()


def get_quality_assessment_prompt() -> str:
    """获取质量评估提示词"""
    return ReviewPrompts.get_quality_assessment_prompt()
