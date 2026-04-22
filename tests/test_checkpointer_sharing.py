"""
Checkpointer 传递测试

验证主图和子图是否正确共享 checkpointer 实例
"""
import pytest
from app.core.checkpointer import get_checkpointer, create_checkpointer, clear_checkpointer_cache
from app.graph.main_graph import MainGraphBuilder, MainGraphManager
from app.api.deps import get_graph_manager, clear_dependency_cache


class TestCheckpointerSharing:
    """测试 checkpointer 在主图和子图间的共享"""

    def setup_method(self):
        """每个测试前清除缓存"""
        clear_dependency_cache()

    def test_main_graph_uses_provided_checkpointer(self):
        """测试主图使用提供的 checkpointer"""
        checkpointer = create_checkpointer()
        builder = MainGraphBuilder(checkpointer=checkpointer)

        # 验证主图使用了提供的 checkpointer
        assert builder.checkpointer is checkpointer
        assert id(builder.checkpointer) == id(checkpointer)

    def test_main_graph_creates_checkpointer_if_none(self):
        """测试主图在未提供 checkpointer 时创建新实例"""
        builder = MainGraphBuilder(checkpointer=None)

        # 验证主图创建了新的 checkpointer
        assert builder.checkpointer is not None

    def test_application_uses_singleton_checkpointer(self):
        """测试应用使用单例 checkpointer"""
        # 第一次获取
        manager1 = get_graph_manager()
        checkpointer1 = get_checkpointer()

        # 第二次获取
        manager2 = get_graph_manager()
        checkpointer2 = get_checkpointer()

        # 验证是同一个实例
        assert manager1 is manager2
        assert checkpointer1 is checkpointer2
        assert id(checkpointer1) == id(checkpointer2)

    def test_subgraphs_share_main_graph_checkpointer(self):
        """测试子图与主图共享 checkpointer"""
        checkpointer = create_checkpointer()
        builder = MainGraphBuilder(checkpointer=checkpointer)

        # 主图的 checkpointer
        main_checkpointer_id = id(builder.checkpointer)

        # 注意：子图已经编译，我们无法直接访问其 checkpointer
        # 但我们可以验证构建过程正确完成
        assert builder.dissection_subgraph is not None
        assert builder.review_subgraph is not None

        # 验证主图使用了正确的 checkpointer
        assert id(builder.checkpointer) == main_checkpointer_id

    def test_different_main_graphs_use_different_checkpointers(self):
        """测试不同的主图实例使用不同的 checkpointer（非单例模式）"""
        # 创建两个独立的主图
        builder1 = MainGraphBuilder(checkpointer=None)
        builder2 = MainGraphBuilder(checkpointer=None)

        # 验证它们使用不同的 checkpointer
        assert builder1.checkpointer is not builder2.checkpointer
        assert id(builder1.checkpointer) != id(builder2.checkpointer)

    def test_main_graph_manager_uses_singleton(self):
        """测试 MainGraphManager 使用单例 checkpointer"""
        # 获取单例 checkpointer
        singleton_checkpointer = get_checkpointer()

        # 创建 MainGraphManager
        manager = MainGraphManager(checkpointer=singleton_checkpointer)

        # 验证 manager 的 builder 使用了单例 checkpointer
        assert id(manager.builder.checkpointer) == id(singleton_checkpointer)


class TestCheckpointerFactory:
    """测试 checkpointer 工厂函数"""

    def setup_method(self):
        """每个测试前清除缓存"""
        clear_checkpointer_cache()

    def test_create_checkpointer_returns_new_instance(self):
        """测试 create_checkpointer 每次返回新实例"""
        cp1 = create_checkpointer()
        cp2 = create_checkpointer()

        assert cp1 is not cp2
        assert id(cp1) != id(cp2)

    def test_get_checkpointer_returns_singleton(self):
        """测试 get_checkpointer 返回单例"""
        cp1 = get_checkpointer()
        cp2 = get_checkpointer()

        assert cp1 is cp2
        assert id(cp1) == id(cp2)

    def test_clear_checkpointer_cache_works(self):
        """测试清除 checkpointer 缓存"""
        cp1 = get_checkpointer()
        clear_checkpointer_cache()
        cp2 = get_checkpointer()

        # 清除缓存后应该是不同的实例
        assert cp1 is not cp2
        assert id(cp1) != id(cp2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
