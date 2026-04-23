"""
测试 LangGraph 的状态更新机制
"""
import asyncio
from typing_extensions import TypedDict
from langgraph.graph import StateGraph


class TestState(TypedDict):
    task_id: str
    counter: int
    data: dict


async def node1(state: TestState) -> TestState:
    """第一个节点：修改 counter"""
    print(f"node1 接收: {state}")
    new_state = state.copy()
    new_state['counter'] = state['counter'] + 1
    print(f"node1 返回: {new_state}")
    return new_state


async def node2(state: TestState) -> TestState:
    """第二个节点：修改 data"""
    print(f"node2 接收: {state}")
    new_state = state.copy()
    new_data = state['data'].copy()
    new_data['key2'] = 'value2'
    new_state['data'] = new_data
    print(f"node2 返回: {new_state}")
    return new_state


async def test_state_flow():
    """测试状态流转"""
    # 创建图
    graph = StateGraph(TestState)
    graph.add_node("node1", node1)
    graph.add_node("node2", node2)
    graph.set_entry_point("node1")
    graph.add_edge("node1", "node2")
    graph.set_finish_point("node2")

    compiled = graph.compile()

    # 初始状态
    initial_state = TestState(
        task_id="test-123",
        counter=0,
        data={'key1': 'value1'}
    )

    print("=" * 60)
    print("初始状态:", initial_state)
    print("=" * 60)

    # 执行
    result = await compiled.ainvoke(initial_state)

    print("=" * 60)
    print("最终状态:", result)
    print("=" * 60)

    # 验证
    assert 'task_id' in result, "task_id 丢失了！"
    assert result['task_id'] == 'test-123', f"task_id 被修改了: {result['task_id']}"
    assert result['counter'] == 1, f"counter 错误: {result['counter']}"
    assert 'key2' in result['data'], "data.key2 丢失了！"

    print("✓ 所有字段都正确保留")


if __name__ == "__main__":
    asyncio.run(test_state_flow())
