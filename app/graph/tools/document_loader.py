"""
文档解析器模块

支持多种格式的文档解析，包括代码字符串、Markdown 等格式。
用于 AlgoWeaver AI 系统的代码分析和算法讲解功能。
"""

import re
import ast
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import markdown
except ImportError:
    markdown = None


class DocumentType(Enum):
    """文档类型枚举"""
    PYTHON_CODE = "python_code"
    JAVASCRIPT_CODE = "javascript_code"
    JAVA_CODE = "java_code"
    CPP_CODE = "cpp_code"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    JSON = "json"
    UNKNOWN = "unknown"


class CodeLanguage(Enum):
    """支持的编程语言"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    TYPESCRIPT = "typescript"


@dataclass
class ParsedCode:
    """解析后的代码结构"""
    language: str
    raw_code: str
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    imports: List[str]
    variables: List[Dict[str, Any]]
    comments: List[str]
    syntax_valid: bool
    error_message: Optional[str] = None


@dataclass
class ParsedMarkdown:
    """解析后的 Markdown 结构"""
    title: Optional[str]
    headers: List[Dict[str, Any]]
    code_blocks: List[Dict[str, Any]]
    text_content: str
    links: List[Dict[str, str]]
    images: List[Dict[str, str]]


@dataclass
class DocumentParseResult:
    """文档解析结果"""
    document_type: DocumentType
    content: Union[ParsedCode, ParsedMarkdown, Dict[str, Any], str]
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class DocumentLoader:
    """
    文档解析器工具
    
    支持多种格式的文档解析，包括：
    - Python/Java/JavaScript/C++ 代码
    - Markdown 文档
    - 纯文本
    - JSON 数据
    """

    name: str
    description: str
    supported_languages: Dict[str, List[str]]
    
    def __init__(self):
        super().__init__()
        self.name = "document_loader"
        self.description = "解析各种格式的文档，包括代码文件、Markdown 文档等"
        self.supported_languages = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'cpp': ['.cpp', '.cc', '.cxx'],
            'c': ['.c'],
            'markdown': ['.md', '.markdown'],
            'json': ['.json']
        }
    
    def run(self, content: str, document_type: Optional[str] = None, 
            filename: Optional[str] = None) -> DocumentParseResult:
        """
        解析文档内容
        
        Args:
            content: 文档内容字符串
            document_type: 指定文档类型，如果不指定则自动检测
            filename: 文件名，用于类型推断
            
        Returns:
            DocumentParseResult: 解析结果
        """
        try:
            # 检测文档类型
            detected_type = self._detect_document_type(content, document_type, filename)
            
            # 根据类型进行解析
            if detected_type == DocumentType.PYTHON_CODE:
                result = self._parse_python_code(content)
            elif detected_type in [DocumentType.JAVASCRIPT_CODE, DocumentType.JAVA_CODE, DocumentType.CPP_CODE]:
                result = self._parse_generic_code(content, detected_type.value.replace('_code', ''))
            elif detected_type == DocumentType.MARKDOWN:
                result = self._parse_markdown(content)
            elif detected_type == DocumentType.JSON:
                result = self._parse_json(content)
            else:
                result = self._parse_plain_text(content)
            
            return DocumentParseResult(
                document_type=detected_type,
                content=result,
                metadata=self._extract_metadata(content, detected_type),
                success=True
            )
            
        except Exception as e:
            return DocumentParseResult(
                document_type=DocumentType.UNKNOWN,
                content="",
                metadata={},
                success=False,
                error_message=str(e)
            )

    
    def _detect_document_type(self, content: str, document_type: Optional[str] = None, 
                            filename: Optional[str] = None) -> DocumentType:
        """
        检测文档类型
        
        Args:
            content: 文档内容
            document_type: 指定的文档类型
            filename: 文件名
            
        Returns:
            DocumentType: 检测到的文档类型
        """
        # 如果明确指定了类型
        if document_type:
            try:
                return DocumentType(document_type.lower())
            except ValueError:
                pass
        
        # 根据文件扩展名判断
        if filename:
            for lang, extensions in self.supported_languages.items():
                if any(filename.lower().endswith(ext) for ext in extensions):
                    if lang == 'python':
                        return DocumentType.PYTHON_CODE
                    elif lang in ['javascript', 'typescript']:
                        return DocumentType.JAVASCRIPT_CODE
                    elif lang == 'java':
                        return DocumentType.JAVA_CODE
                    elif lang in ['cpp', 'c']:
                        return DocumentType.CPP_CODE
                    elif lang == 'markdown':
                        return DocumentType.MARKDOWN
                    elif lang == 'json':
                        # 对于 JSON 文件，先检查内容是否真的是 JSON
                        try:
                            json.loads(content)
                            return DocumentType.JSON
                        except:
                            # 如果不是有效 JSON，继续其他检测
                            pass
        
        # 根据内容特征判断
        content_lower = content.strip().lower()
        
        # JSON 检测
        if (content_lower.startswith('{') and content_lower.endswith('}')) or \
           (content_lower.startswith('[') and content_lower.endswith(']')):
            try:
                json.loads(content)
                return DocumentType.JSON
            except:
                pass
        
        # Markdown 检测
        if re.search(r'^#{1,6}\s+', content, re.MULTILINE) or \
           '```' in content or \
           re.search(r'\[.*\]\(.*\)', content):
            return DocumentType.MARKDOWN
        
        # Python 代码检测
        python_keywords = ['def ', 'class ', 'import ', 'from ', 'if __name__']
        if any(keyword in content for keyword in python_keywords):
            return DocumentType.PYTHON_CODE
        
        # Java 代码检测
        java_keywords = ['public class', 'private class', 'public static void main', 'package ']
        if any(keyword in content for keyword in java_keywords):
            return DocumentType.JAVA_CODE
        
        # JavaScript 代码检测
        js_keywords = ['function ', 'const ', 'let ', 'var ', '=>', 'console.log']
        if any(keyword in content for keyword in js_keywords):
            return DocumentType.JAVASCRIPT_CODE
        
        # C++ 代码检测
        cpp_keywords = ['#include', 'using namespace', 'int main()', 'std::']
        if any(keyword in content for keyword in cpp_keywords):
            return DocumentType.CPP_CODE
        
        return DocumentType.PLAIN_TEXT
    
    def _parse_python_code(self, code: str) -> ParsedCode:
        """
        解析 Python 代码
        
        Args:
            code: Python 代码字符串
            
        Returns:
            ParsedCode: 解析结果
        """
        functions = []
        classes = []
        imports = []
        variables = []
        comments = []
        syntax_valid = True
        error_message = None
        
        try:
            # 解析 AST
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # 解析函数定义
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'line_number': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'docstring': ast.get_docstring(node),
                        'decorators': [ast.unparse(dec) for dec in node.decorator_list] if hasattr(ast, 'unparse') else []
                    }
                    functions.append(func_info)
                
                # 解析类定义
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'line_number': node.lineno,
                        'bases': [ast.unparse(base) for base in node.bases] if hasattr(ast, 'unparse') else [],
                        'docstring': ast.get_docstring(node),
                        'methods': []
                    }
                    
                    # 解析类方法
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                'name': item.name,
                                'line_number': item.lineno,
                                'args': [arg.arg for arg in item.args.args],
                                'docstring': ast.get_docstring(item)
                            }
                            class_info['methods'].append(method_info)
                    
                    classes.append(class_info)
                
                # 解析导入语句
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"from {module} import {alias.name}")
                
                # 解析变量赋值
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_info = {
                                'name': target.id,
                                'line_number': node.lineno,
                                'type': 'assignment'
                            }
                            variables.append(var_info)
            
            # 提取注释
            comments = self._extract_comments(code)
            
        except SyntaxError as e:
            syntax_valid = False
            error_message = f"语法错误: {str(e)}"
        except Exception as e:
            syntax_valid = False
            error_message = f"解析错误: {str(e)}"
        
        return ParsedCode(
            language="python",
            raw_code=code,
            functions=functions,
            classes=classes,
            imports=imports,
            variables=variables,
            comments=comments,
            syntax_valid=syntax_valid,
            error_message=error_message
        )
    
    def _parse_generic_code(self, code: str, language: str) -> ParsedCode:
        """
        解析通用代码（非 Python）
        
        Args:
            code: 代码字符串
            language: 编程语言
            
        Returns:
            ParsedCode: 解析结果
        """
        functions = []
        classes = []
        imports = []
        variables = []
        comments = self._extract_comments(code)
        
        # 简单的正则表达式解析（可以根据需要扩展）
        if language == "java":
            # Java 函数解析
            func_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{'
            functions = [{'name': match.group(1), 'language': 'java'} 
                        for match in re.finditer(func_pattern, code)]
            
            # Java 类解析
            class_pattern = r'(?:public|private)?\s*class\s+(\w+)'
            classes = [{'name': match.group(1), 'language': 'java'} 
                      for match in re.finditer(class_pattern, code)]
            
            # Java 导入解析
            import_pattern = r'import\s+([^;]+);'
            imports = [match.group(1) for match in re.finditer(import_pattern, code)]
        
        elif language == "javascript":
            # JavaScript 函数解析
            func_pattern = r'function\s+(\w+)\s*\([^)]*\)|const\s+(\w+)\s*=\s*\([^)]*\)\s*=>'
            for match in re.finditer(func_pattern, code):
                name = match.group(1) or match.group(2)
                if name:
                    functions.append({'name': name, 'language': 'javascript'})
            
            # JavaScript 类解析
            class_pattern = r'class\s+(\w+)'
            classes = [{'name': match.group(1), 'language': 'javascript'} 
                      for match in re.finditer(class_pattern, code)]
        
        return ParsedCode(
            language=language,
            raw_code=code,
            functions=functions,
            classes=classes,
            imports=imports,
            variables=variables,
            comments=comments,
            syntax_valid=True  # 简单解析，假设语法正确
        )
    
    def _parse_markdown(self, content: str) -> ParsedMarkdown:
        """
        解析 Markdown 文档
        
        Args:
            content: Markdown 内容
            
        Returns:
            ParsedMarkdown: 解析结果
        """
        # 提取标题
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else None
        
        # 提取所有标题
        headers = []
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2)
            headers.append({
                'level': level,
                'text': text,
                'line_number': content[:match.start()].count('\n') + 1
            })
        
        # 提取代码块
        code_blocks = []
        for match in re.finditer(r'```(\w+)?\n(.*?)\n```', content, re.DOTALL):
            language = match.group(1) or 'text'
            code = match.group(2)
            code_blocks.append({
                'language': language,
                'code': code,
                'line_number': content[:match.start()].count('\n') + 1
            })
        
        # 提取链接（排除图片链接）
        links = []
        for match in re.finditer(r'(?<!\!)\[([^\]]+)\]\(([^)]+)\)', content):
            links.append({
                'text': match.group(1),
                'url': match.group(2)
            })
        
        # 提取图片
        images = []
        for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content):
            images.append({
                'alt': match.group(1),
                'url': match.group(2)
            })
        
        # 转换为 HTML 并提取纯文本（如果有 markdown 库）
        if markdown:
            html = markdown.markdown(content)
            text_content = re.sub(r'<[^>]+>', '', html)
        else:
            # 简单的文本提取，移除 Markdown 标记
            text_content = re.sub(r'[#*`\[\]()!]', '', content)
            text_content = re.sub(r'\n+', '\n', text_content)
        
        return ParsedMarkdown(
            title=title,
            headers=headers,
            code_blocks=code_blocks,
            text_content=text_content.strip(),
            links=links,
            images=images
        )
    
    def _parse_json(self, content: str) -> Dict[str, Any]:
        """
        解析 JSON 内容
        
        Args:
            content: JSON 字符串
            
        Returns:
            Dict: 解析后的 JSON 对象
        """
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析错误: {str(e)}")
    
    def _parse_plain_text(self, content: str) -> str:
        """
        解析纯文本
        
        Args:
            content: 文本内容
            
        Returns:
            str: 清理后的文本内容
        """
        # 简单的文本清理
        lines = content.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        return '\n'.join(cleaned_lines)
    
    def _extract_comments(self, code: str) -> List[str]:
        """
        提取代码中的注释
        
        Args:
            code: 代码字符串
            
        Returns:
            List[str]: 注释列表
        """
        comments = []
        
        # 单行注释
        for match in re.finditer(r'#(.+)$', code, re.MULTILINE):
            comments.append(match.group(1).strip())
        
        # 多行注释/文档字符串
        for match in re.finditer(r'"""(.*?)"""', code, re.DOTALL):
            comments.append(match.group(1).strip())
        
        for match in re.finditer(r"'''(.*?)'''", code, re.DOTALL):
            comments.append(match.group(1).strip())
        
        return comments
    
    def _extract_metadata(self, content: str, doc_type: DocumentType) -> Dict[str, Any]:
        """
        提取文档元数据
        
        Args:
            content: 文档内容
            doc_type: 文档类型
            
        Returns:
            Dict: 元数据字典
        """
        metadata = {
            'length': len(content),
            'lines': content.count('\n') + 1,
            'words': len(content.split()),
            'document_type': doc_type.value
        }
        
        if doc_type in [DocumentType.PYTHON_CODE, DocumentType.JAVASCRIPT_CODE, 
                       DocumentType.JAVA_CODE, DocumentType.CPP_CODE]:
            # 代码特定的元数据
            metadata.update({
                'has_functions': bool(re.search(r'def |function |public .* \(', content)),
                'has_classes': bool(re.search(r'class |public class', content)),
                'has_imports': bool(re.search(r'import |#include|from .* import', content))
            })
        
        elif doc_type == DocumentType.MARKDOWN:
            # Markdown 特定的元数据
            metadata.update({
                'has_code_blocks': '```' in content,
                'has_links': bool(re.search(r'\[.*\]\(.*\)', content)),
                'has_images': bool(re.search(r'!\[.*\]\(.*\)', content)),
                'header_count': len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE))
            })
        
        return metadata


# 便捷函数
def parse_document(content: str, document_type: Optional[str] = None, 
                  filename: Optional[str] = None) -> DocumentParseResult:
    """
    解析文档的便捷函数
    
    Args:
        content: 文档内容
        document_type: 文档类型（可选）
        filename: 文件名（可选）
        
    Returns:
        DocumentParseResult: 解析结果
    """
    loader = DocumentLoader()
    return loader.run(content, document_type, filename)


def parse_code(code: str, language: str) -> ParsedCode:
    """
    解析代码的便捷函数
    
    Args:
        code: 代码字符串
        language: 编程语言
        
    Returns:
        ParsedCode: 解析结果
    """
    loader = DocumentLoader()
    result = loader.run(code, f"{language}_code")
    
    if result.success and isinstance(result.content, ParsedCode):
        return result.content
    else:
        raise ValueError(f"代码解析失败: {result.error_message}")


def parse_markdown(content: str) -> ParsedMarkdown:
    """
    解析 Markdown 的便捷函数
    
    Args:
        content: Markdown 内容
        
    Returns:
        ParsedMarkdown: 解析结果
    """
    loader = DocumentLoader()
    result = loader.run(content, "markdown")
    
    if result.success and isinstance(result.content, ParsedMarkdown):
        return result.content
    else:
        raise ValueError(f"Markdown 解析失败: {result.error_message}")