"""
算法拆解子图 Agent 提示词模板

本模块定义算法拆解子图中各个 Agent 专用的系统提示词，包括：
- Step Simulator Agent: 算法步骤模拟提示词
- Visual Generator Agent: 可视化生成提示词
"""

from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any


class DissectionPrompts:
    """算法拆解子图提示词模板集合"""

    @staticmethod
    def get_simulation_prompt() -> ChatPromptTemplate:
        """
        算法模拟提示词

        用于分析代码并模拟算法的逐步执行过程。
        """
        return ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的算法分析专家。你的任务是分析给定的代码，并详细模拟其执行过程。

请按照以下步骤进行分析：
1. 识别算法的核心逻辑和数据结构
2. 分析算法的执行流程和关键步骤
3. 追踪重要变量的变化过程
4. 识别循环、递归和条件判断的执行模式
5. 分析算法的时间和空间复杂度

输出格式要求：
- 将执行过程分解为清晰的步骤
- 每个步骤包含：步骤类型、描述、变量状态、代码行号
- 提供变量追踪信息
- 给出性能分析结果

请确保分析准确、详细且易于理解。"""),
            ("human", "请分析以下代码的执行过程：\n\n```python\n{code}\n```\n\n输入数据：{input_data}")
        ])

    @staticmethod
    def get_visualization_prompt() -> ChatPromptTemplate:
        """
        可视化生成提示词

        用于根据算法模拟结果生成可视化的伪代码讲解和教学材料。
        """
        return ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的算法教学专家。你的任务是根据算法的执行步骤，生成清晰易懂的教学材料。

请生成以下内容：
1. 结构化的伪代码，突出算法的核心逻辑
2. 每个关键步骤的详细解释
3. 时间复杂度和空间复杂度分析
4. 算法的可视化描述（如果适用）
5. 教学要点和注意事项

输出要求：
- 使用清晰的 Markdown 格式
- 伪代码要简洁但完整
- 解释要通俗易懂，适合教学
- 包含具体的复杂度分析过程
- 提供学习建议和扩展思考"""),
            ("human", """请为以下算法生成教学材料：

代码：
```python
{code}
```

执行步骤：
{execution_steps}

变量追踪：
{variables_trace}

请生成完整的教学讲解。""")
        ])

    @staticmethod
    def get_pseudocode_generation_prompt() -> str:
        """
        伪代码生成提示词模板

        Returns:
            伪代码生成的提示词字符串模板
        """
        return """请为以下 Python 代码生成清晰的伪代码：

```python
{code}
```

要求：
1. 使用标准的伪代码格式
2. 突出算法的核心逻辑
3. 保持结构清晰，层次分明
4. 使用中文注释说明关键步骤
"""

    @staticmethod
    def get_complexity_analysis_prompt() -> str:
        """
        复杂度分析提示词模板

        Returns:
            复杂度分析的提示词字符串模板
        """
        return """请分析以下代码的时间复杂度和空间复杂度：

```python
{code}
```

请提供：
1. 时间复杂度分析过程和结果
2. 空间复杂度分析过程和结果
3. 最坏情况、平均情况、最好情况的分析（如果有差异）

请用大O记号表示最终结果。
"""

    @staticmethod
    def get_teaching_notes_prompt() -> str:
        """
        教学要点生成提示词模板

        Returns:
            教学要点生成的提示词字符串模板
        """
        return """请为以下算法生成教学要点和学习建议：

```python
{code}
```

请提供：
1. 算法的核心思想和设计理念
2. 关键的实现技巧和注意事项
3. 常见的错误和陷阱
4. 相关的算法和扩展思考
5. 实际应用场景

每个要点用一句话简洁表达。
"""


# 便捷函数，用于获取提示词模板

def get_simulation_prompt() -> ChatPromptTemplate:
    """获取算法模拟提示词"""
    return DissectionPrompts.get_simulation_prompt()


def get_visualization_prompt() -> ChatPromptTemplate:
    """获取可视化生成提示词"""
    return DissectionPrompts.get_visualization_prompt()


def get_pseudocode_generation_prompt() -> str:
    """获取伪代码生成提示词"""
    return DissectionPrompts.get_pseudocode_generation_prompt()


def get_complexity_analysis_prompt() -> str:
    """获取复杂度分析提示词"""
    return DissectionPrompts.get_complexity_analysis_prompt()


def get_teaching_notes_prompt() -> str:
    """获取教学要点生成提示词"""
    return DissectionPrompts.get_teaching_notes_prompt()
