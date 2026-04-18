"""
文档解析器单元测试

测试 DocumentLoader 的各种功能，包括代码解析、Markdown 解析和自动类型检测。
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.graph.tools.document_loader import (
    DocumentLoader, DocumentType, ParsedCode, ParsedMarkdown,
    parse_document, parse_code, parse_markdown
)


class TestDocumentLoader:
    """文档解析器测试类"""
    
    def setup_method(self):
        """测试前的设置"""
        self.loader = DocumentLoader()
    
    def test_python_code_parsing(self):
        """测试 Python 代码解析"""
        python_code = '''
def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        return a + b
'''
        
        result = self.loader.run(python_code, "python_code")
        
        assert result.success is True
        assert result.document_type == DocumentType.PYTHON_CODE
        assert isinstance(result.content, ParsedCode)
        
        parsed_code = result.content
        assert parsed_code.syntax_valid is True
        assert len(parsed_code.functions) == 3  # fibonacci, __init__, add
        assert len(parsed_code.classes) == 1    # Calculator
        assert parsed_code.language == "python"
        
        # 检查函数名
        function_names = [func['name'] for func in parsed_code.functions]
        assert 'fibonacci' in function_names
        assert '__init__' in function_names
        assert 'add' in function_names
        
        # 检查类名
        class_names = [cls['name'] for cls in parsed_code.classes]
        assert 'Calculator' in class_names
    
    def test_python_syntax_error(self):
        """测试 Python 语法错误处理"""
        invalid_code = '''
def broken_function(
    # 缺少闭合括号
    return "error"
'''
        
        result = self.loader.run(invalid_code, "python_code")
        
        assert result.success is True  # 解析过程成功
        assert isinstance(result.content, ParsedCode)
        
        parsed_code = result.content
        assert parsed_code.syntax_valid is False
        assert parsed_code.error_message is not None
        assert "语法错误" in parsed_code.error_message
    
    def test_markdown_parsing(self):
        """测试 Markdown 解析"""
        markdown_content = '''
# 主标题

## 二级标题

这是一段文本。

### 代码示例

```python
def hello():
    print("Hello, World!")
```

更多信息请访问 [官网](https://example.com)。

![图片](https://example.com/image.png)
'''
        
        result = self.loader.run(markdown_content, "markdown")
        
        assert result.success is True
        assert result.document_type == DocumentType.MARKDOWN
        assert isinstance(result.content, ParsedMarkdown)
        
        parsed_md = result.content
        assert parsed_md.title == "主标题"
        assert len(parsed_md.headers) == 3
        assert len(parsed_md.code_blocks) == 1
        assert len(parsed_md.links) == 1
        assert len(parsed_md.images) == 1
        
        # 检查代码块
        code_block = parsed_md.code_blocks[0]
        assert code_block['language'] == 'python'
        assert 'def hello():' in code_block['code']
        
        # 检查链接
        link = parsed_md.links[0]
        assert link['text'] == '官网'
        assert link['url'] == 'https://example.com'
    
    def test_javascript_code_parsing(self):
        """测试 JavaScript 代码解析"""
        js_code = '''
function calculateSum(a, b) {
    return a + b;
}

const multiply = (x, y) => x * y;

class MathUtils {
    constructor() {
        this.pi = 3.14159;
    }
}
'''
        
        result = self.loader.run(js_code, "javascript_code")
        
        assert result.success is True
        assert result.document_type == DocumentType.JAVASCRIPT_CODE
        assert isinstance(result.content, ParsedCode)
        
        parsed_code = result.content
        assert parsed_code.language == "javascript"
        assert len(parsed_code.functions) >= 1  # 至少检测到一个函数
        assert len(parsed_code.classes) >= 1    # 至少检测到一个类
    
    def test_json_parsing(self):
        """测试 JSON 解析"""
        json_content = '''
{
    "name": "AlgoWeaver",
    "version": "1.0.0",
    "features": ["code_analysis", "optimization"],
    "config": {
        "timeout": 30,
        "max_iterations": 5
    }
}
'''
        
        result = self.loader.run(json_content, "json")
        
        assert result.success is True
        assert result.document_type == DocumentType.JSON
        assert isinstance(result.content, dict)
        
        parsed_json = result.content
        assert parsed_json['name'] == 'AlgoWeaver'
        assert parsed_json['version'] == '1.0.0'
        assert 'features' in parsed_json
        assert 'config' in parsed_json
    
    def test_auto_type_detection(self):
        """测试自动类型检测"""
        test_cases = [
            ("def test(): pass", DocumentType.PYTHON_CODE),
            ("function test() { return 42; }", DocumentType.JAVASCRIPT_CODE),
            ("# 标题\n\n内容", DocumentType.MARKDOWN),
            ('{"key": "value"}', DocumentType.JSON),
            ("这是普通文本内容", DocumentType.PLAIN_TEXT)
        ]
        
        for content, expected_type in test_cases:
            result = self.loader.run(content)
            assert result.success is True
            assert result.document_type == expected_type
    
    def test_filename_based_detection(self):
        """测试基于文件名的类型检测"""
        # 测试不同文件扩展名
        test_cases = [
            ("print('hello')", "test.py", DocumentType.PYTHON_CODE),
            ("function test() { return 42; }", "test.js", DocumentType.JAVASCRIPT_CODE),
            ("public class Test {}", "test.java", DocumentType.JAVA_CODE),
            ("# 标题\n\n内容", "test.md", DocumentType.MARKDOWN),
            ('{"key": "value"}', "test.json", DocumentType.JSON)
        ]
        
        for content, filename, expected_type in test_cases:
            result = self.loader.run(content, filename=filename)
            assert result.success is True, f"解析失败: {result.error_message}"
            assert result.document_type == expected_type
    
    def test_metadata_extraction(self):
        """测试元数据提取"""
        python_code = '''
def test_function():
    """测试函数"""
    pass

class TestClass:
    pass
'''
        
        result = self.loader.run(python_code, "python_code")
        
        assert result.success is True
        assert 'length' in result.metadata
        assert 'lines' in result.metadata
        assert 'words' in result.metadata
        assert 'has_functions' in result.metadata
        assert 'has_classes' in result.metadata
        
        assert result.metadata['has_functions'] is True
        assert result.metadata['has_classes'] is True
    
    def test_convenience_functions(self):
        """测试便捷函数"""
        # 测试 parse_code
        python_code = "def hello(): pass"
        parsed_code = parse_code(python_code, "python")
        assert isinstance(parsed_code, ParsedCode)
        assert parsed_code.language == "python"
        
        # 测试 parse_markdown
        markdown_content = "# 标题\n\n内容"
        parsed_md = parse_markdown(markdown_content)
        assert isinstance(parsed_md, ParsedMarkdown)
        assert parsed_md.title == "标题"
        
        # 测试 parse_document
        result = parse_document(python_code, "python_code")
        assert result.success is True
        assert result.document_type == DocumentType.PYTHON_CODE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])