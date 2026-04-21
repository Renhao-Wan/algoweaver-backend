"""
输出解析工具模块

提供 LLM 输出的结构化解析、格式化和验证功能。
支持多种输出格式的解析和转换。
"""

import re
import json
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, ValidationError

from app.core.logger import get_logger

logger = get_logger(__name__)


class OutputFormat(str, Enum):
    """输出格式枚举"""
    JSON = "json"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    CODE_BLOCK = "code_block"


class ParsedOutput(BaseModel):
    """解析后的输出模型"""

    format: OutputFormat
    content: Union[Dict[str, Any], str, List[Any]]
    metadata: Dict[str, Any] = {}
    is_valid: bool = True
    errors: List[str] = []


class OutputParser:
    """
    输出解析器

    提供 LLM 输出的解析、验证和格式化功能。
    """

    @staticmethod
    def parse_json(text: str, strict: bool = True) -> ParsedOutput:
        """
        解析 JSON 格式输出

        Args:
            text: 待解析文本
            strict: 是否严格模式（严格模式下解析失败会抛出异常）

        Returns:
            ParsedOutput: 解析结果
        """
        try:
            # 尝试提取 JSON 代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # 尝试提取花括号或方括号包裹的内容
                json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                else:
                    json_text = text

            # 解析 JSON
            content = json.loads(json_text)

            return ParsedOutput(
                format=OutputFormat.JSON,
                content=content,
                is_valid=True
            )

        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {str(e)}"
            logger.warning(error_msg)

            if strict:
                raise ValueError(error_msg)

            return ParsedOutput(
                format=OutputFormat.JSON,
                content=text,
                is_valid=False,
                errors=[error_msg]
            )

    @staticmethod
    def parse_markdown(text: str) -> ParsedOutput:
        """
        解析 Markdown 格式输出

        Args:
            text: 待解析文本

        Returns:
            ParsedOutput: 解析结果
        """
        # 提取标题
        headers = re.findall(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE)

        # 提取代码块
        code_blocks = re.findall(r'```(\w+)?\s*(.*?)```', text, re.DOTALL)

        # 提取列表项
        list_items = re.findall(r'^[\*\-\+]\s+(.+)$', text, re.MULTILINE)

        metadata = {
            "headers": [{"level": len(h[0]), "text": h[1]} for h in headers],
            "code_blocks": [{"language": cb[0] or "text", "code": cb[1].strip()} for cb in code_blocks],
            "list_items": list_items
        }

        return ParsedOutput(
            format=OutputFormat.MARKDOWN,
            content=text,
            metadata=metadata,
            is_valid=True
        )

    @staticmethod
    def parse_code_block(text: str, language: Optional[str] = None) -> ParsedOutput:
        """
        解析代码块

        Args:
            text: 待解析文本
            language: 指定编程语言

        Returns:
            ParsedOutput: 解析结果
        """
        # 尝试提取代码块
        if language:
            pattern = rf'```{language}\s*(.*?)\s*```'
        else:
            pattern = r'```(\w+)?\s*(.*?)```'

        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            if language:
                # 单语言模式
                code_blocks = [{"language": language, "code": match.strip()} for match in matches]
            else:
                # 多语言模式
                code_blocks = [{"language": m[0] or "text", "code": m[1].strip()} for m in matches]

            return ParsedOutput(
                format=OutputFormat.CODE_BLOCK,
                content=code_blocks,
                metadata={"count": len(code_blocks)},
                is_valid=True
            )
        else:
            # 没有找到代码块，返回原文本
            return ParsedOutput(
                format=OutputFormat.CODE_BLOCK,
                content=[{"language": language or "text", "code": text.strip()}],
                is_valid=True
            )

    @staticmethod
    def extract_sections(text: str, section_markers: List[str]) -> Dict[str, str]:
        """
        提取文本中的特定章节

        Args:
            text: 待解析文本
            section_markers: 章节标记列表（如 ["## 算法分析", "## 优化建议"]）

        Returns:
            Dict[str, str]: 章节内容字典
        """
        sections = {}

        for i, marker in enumerate(section_markers):
            # 构建正则表达式
            if i < len(section_markers) - 1:
                # 不是最后一个章节，匹配到下一个章节
                next_marker = section_markers[i + 1]
                pattern = rf'{re.escape(marker)}\s*(.*?)\s*(?={re.escape(next_marker)})'
            else:
                # 最后一个章节，匹配到文本末尾
                pattern = rf'{re.escape(marker)}\s*(.*?)$'

            match = re.search(pattern, text, re.DOTALL)
            if match:
                sections[marker] = match.group(1).strip()

        return sections

    @staticmethod
    def validate_structure(
        content: Dict[str, Any],
        required_fields: List[str],
        optional_fields: Optional[List[str]] = None
    ) -> tuple[bool, List[str]]:
        """
        验证结构化内容的完整性

        Args:
            content: 待验证内容
            required_fields: 必需字段列表
            optional_fields: 可选字段列表

        Returns:
            tuple[bool, List[str]]: (是否有效, 错误列表)
        """
        errors = []

        # 检查必需字段
        for field in required_fields:
            if field not in content:
                errors.append(f"缺少必需字段: {field}")
            elif content[field] is None or content[field] == "":
                errors.append(f"必需字段为空: {field}")

        # 检查未知字段
        all_fields = set(required_fields)
        if optional_fields:
            all_fields.update(optional_fields)

        unknown_fields = set(content.keys()) - all_fields
        if unknown_fields:
            logger.debug(f"发现未知字段: {unknown_fields}")

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def format_as_markdown(data: Dict[str, Any], title: Optional[str] = None) -> str:
        """
        将结构化数据格式化为 Markdown

        Args:
            data: 结构化数据
            title: 文档标题

        Returns:
            str: Markdown 格式文本
        """
        lines = []

        # 添加标题
        if title:
            lines.append(f"# {title}\n")

        # 递归格式化数据
        def format_value(key: str, value: Any, level: int = 2):
            indent = "  " * (level - 2)

            if isinstance(value, dict):
                lines.append(f"{'#' * level} {key}\n")
                for k, v in value.items():
                    format_value(k, v, level + 1)
            elif isinstance(value, list):
                lines.append(f"{'#' * level} {key}\n")
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            lines.append(f"{indent}- **{k}**: {v}")
                    else:
                        lines.append(f"{indent}- {item}")
                lines.append("")
            else:
                lines.append(f"{'#' * level} {key}\n")
                lines.append(f"{value}\n")

        for key, value in data.items():
            format_value(key, value)

        return "\n".join(lines)

    @staticmethod
    def clean_llm_output(text: str) -> str:
        """
        清理 LLM 输出中的多余内容

        Args:
            text: 原始输出

        Returns:
            str: 清理后的文本
        """
        # 移除多余的空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 移除首尾空白
        text = text.strip()

        # 移除常见的 LLM 前缀
        prefixes = [
            r'^(Sure|Certainly|Of course)[,!]?\s*',
            r'^(Here is|Here\'s)\s+',
            r'^(Let me|I will|I\'ll)\s+',
        ]
        for prefix in prefixes:
            text = re.sub(prefix, '', text, flags=re.IGNORECASE)

        return text

    @staticmethod
    def extract_key_value_pairs(text: str) -> Dict[str, str]:
        """
        从文本中提取键值对

        支持格式：
        - Key: Value
        - **Key**: Value
        - Key = Value

        Args:
            text: 待解析文本

        Returns:
            Dict[str, str]: 键值对字典
        """
        pairs = {}

        # 匹配多种格式
        patterns = [
            r'\*\*(.+?)\*\*:\s*(.+?)(?=\n|$)',  # **Key**: Value
            r'(.+?):\s*(.+?)(?=\n|$)',           # Key: Value
            r'(.+?)\s*=\s*(.+?)(?=\n|$)',        # Key = Value
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                if key and value:
                    pairs[key] = value

        return pairs


class StructuredOutputParser:
    """
    结构化输出解析器

    使用 Pydantic 模型进行强类型验证。
    """

    @staticmethod
    def parse_with_model(
        text: str,
        model: type[BaseModel],
        extract_json: bool = True
    ) -> tuple[Optional[BaseModel], List[str]]:
        """
        使用 Pydantic 模型解析输出

        Args:
            text: 待解析文本
            model: Pydantic 模型类
            extract_json: 是否先提取 JSON

        Returns:
            tuple[Optional[BaseModel], List[str]]: (解析结果, 错误列表)
        """
        errors = []

        try:
            # 提取 JSON
            if extract_json:
                parsed = OutputParser.parse_json(text, strict=True)
                data = parsed.content
            else:
                data = json.loads(text)

            # 使用模型验证
            instance = model(**data)
            return instance, []

        except ValidationError as e:
            errors.append(f"模型验证失败: {str(e)}")
        except ValueError as e:
            errors.append(f"JSON 提取失败: {str(e)}")
        except Exception as e:
            errors.append(f"解析失败: {str(e)}")

        return None, errors


# 便捷函数
def parse_json_output(text: str, strict: bool = True) -> ParsedOutput:
    """解析 JSON 输出的便捷函数"""
    return OutputParser.parse_json(text, strict)


def parse_markdown_output(text: str) -> ParsedOutput:
    """解析 Markdown 输出的便捷函数"""
    return OutputParser.parse_markdown(text)


def parse_code_blocks(text: str, language: Optional[str] = None) -> list[Any] | list[dict[str, Any] | str]:
    """提取代码块的便捷函数"""
    result = OutputParser.parse_code_block(text, language)
    return result.content if isinstance(result.content, list) else [result.content]


def clean_output(text: str) -> str:
    """清理输出的便捷函数"""
    return OutputParser.clean_llm_output(text)
