"""
测试状态传递问题
"""
import asyncio
from app.graph.state import StateFactory
from app.graph.supervisor.agent import supervisor_analyze_task_node, supervisor_routing_node


async def test_state_flow():
    """测试状态在节点间的传递"""

    # 1. 创建初始状态
    print("=" * 60)
    print("1. 创建初始状态")
    print("=" * 60)
    state = StateFactory.create_global_state(
        task_id='test-123',
        user_id='test-user',
        code='def bubble_sort(arr): pass',
        language='python',
        optimization_level='balanced'
    )

    print(f"初始状态字段: {list(state.keys())}")
    print(f"task_id: {state.get('task_id')}")
    print(f"current_phase: {state.get('current_phase')}")
    print(f"shared_context: {state.get('shared_context')}")
    print()

    # 2. 执行 supervisor_analyze_task
    print("=" * 60)
    print("2. 执行 supervisor_analyze_task_node")
    print("=" * 60)
    state = await supervisor_analyze_task_node(state)

    print(f"执行后状态字段: {list(state.keys())}")
    print(f"task_id: {state.get('task_id')}")
    print(f"current_phase: {state.get('current_phase')}")
    print(f"shared_context keys: {list(state.get('shared_context', {}).keys())}")
    print(f"last_error: {state.get('last_error')}")
    print()

    # 3. 执行 supervisor_routing
    print("=" * 60)
    print("3. 执行 supervisor_routing_node")
    print("=" * 60)
    state = await supervisor_routing_node(state)

    print(f"执行后状态字段: {list(state.keys())}")
    print(f"task_id: {state.get('task_id')}")
    print(f"current_phase: {state.get('current_phase')}")
    print(f"shared_context keys: {list(state.get('shared_context', {}).keys())}")
    print(f"routing_decision: {state.get('shared_context', {}).get('routing_decision')}")
    print(f"last_error: {state.get('last_error')}")
    print()

    # 4. 测试状态转换
    print("=" * 60)
    print("4. 测试 StateConverter.global_to_dissection")
    print("=" * 60)
    try:
        from app.graph.state import StateConverter
        dissection_state = StateConverter.global_to_dissection(state)
        print(f"转换成功！")
        print(f"dissection_state 字段: {list(dissection_state.keys())}")
        print(f"task_id: {dissection_state.get('task_id')}")
    except Exception as e:
        print(f"转换失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_state_flow())
