"""
WebSocket 路由模块

提供实时通信接口，支持流式输出和 Human-in-the-loop 交互。
"""

from typing import Dict, Any
import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState

from app.services.weaver_service import WeaverService
from app.api.deps import get_graph_manager, get_config
from app.graph.main_graph import MainGraphManager
from app.graph.state import TaskStatus
from app.core.config import Settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(tags=["websocket"])


# ============================================================================
# WebSocket 连接管理
# ============================================================================

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        """初始化连接管理器"""
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        """
        建立连接

        Args:
            task_id: 任务ID
            websocket: WebSocket 连接
        """
        await websocket.accept()
        self.active_connections[task_id] = websocket
        logger.info(f"WebSocket 连接建立: {task_id}")

    def disconnect(self, task_id: str):
        """
        断开连接

        Args:
            task_id: 任务ID
        """
        if task_id in self.active_connections:
            del self.active_connections[task_id]
            logger.info(f"WebSocket 连接断开: {task_id}")

    async def send_message(self, task_id: str, message: Dict[str, Any]):
        """
        发送消息

        Args:
            task_id: 任务ID
            message: 消息内容
        """
        websocket = self.active_connections.get(task_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {task_id}, 错误: {str(e)}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        广播消息

        Args:
            message: 消息内容
        """
        for task_id, websocket in self.active_connections.items():
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"广播消息失败: {task_id}, 错误: {str(e)}")


# 全局连接管理器
manager = ConnectionManager()


# ============================================================================
# 依赖注入
# ============================================================================

def get_weaver_service(
    graph_manager: MainGraphManager = Depends(get_graph_manager),
    settings: Settings = Depends(get_config)
) -> WeaverService:
    """
    获取 Weaver Service 实例

    Args:
        graph_manager: 主图管理器
        settings: 应用配置

    Returns:
        WeaverService: 服务实例
    """
    return WeaverService(graph_manager=graph_manager, settings=settings)


# ============================================================================
# WebSocket 路由
# ============================================================================

@router.websocket("/ws/chat/{task_id}")
async def websocket_chat(
    websocket: WebSocket,
    task_id: str
):
    """
    WebSocket 聊天接口

    提供实时通信，支持流式输出和 Human-in-the-loop 交互。

    Args:
        websocket: WebSocket 连接
        task_id: 任务ID
    """
    # 建立连接
    await manager.connect(task_id, websocket)

    try:
        # 发送连接成功消息
        await manager.send_message(task_id, {
            "type": "connection_established",
            "data": {
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        })

        # 接收和处理消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_json()
                logger.info(f"收到 WebSocket 消息: {task_id}, type={data.get('type')}")

                # 处理不同类型的消息
                message_type = data.get("type")

                if message_type == "start_task":
                    # 启动任务
                    await handle_start_task(task_id, data, websocket)

                elif message_type == "human_decision":
                    # 处理人工决策
                    await handle_human_decision(task_id, data, websocket)

                elif message_type == "cancel_task":
                    # 取消任务
                    await handle_cancel_task(task_id, websocket)
                    break

                elif message_type == "ping":
                    # 心跳检测
                    await manager.send_message(task_id, {
                        "type": "pong",
                        "data": {"timestamp": datetime.utcnow().isoformat()}
                    })

                else:
                    logger.warning(f"未知消息类型: {message_type}")
                    await manager.send_message(task_id, {
                        "type": "error",
                        "data": {"error_message": f"未知消息类型: {message_type}"}
                    })

            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {str(e)}")
                await manager.send_message(task_id, {
                    "type": "error",
                    "data": {"error_message": "消息格式错误"}
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket 客户端断开连接: {task_id}")
        manager.disconnect(task_id)

    except Exception as e:
        logger.error(f"WebSocket 处理异常: {task_id}, 错误: {str(e)}")
        await manager.send_message(task_id, {
            "type": "error",
            "data": {"error_message": str(e)}
        })
        manager.disconnect(task_id)


# ============================================================================
# 消息处理函数
# ============================================================================

async def handle_start_task(task_id: str, data: Dict[str, Any], websocket: WebSocket):
    """
    处理启动任务消息

    Args:
        task_id: 任务ID
        data: 消息数据
        websocket: WebSocket 连接
    """
    try:
        # 提取任务参数
        task_data = data.get("data", {})
        code = task_data.get("code")
        language = task_data.get("language", "python")
        optimization_level = task_data.get("optimization_level", "balanced")

        if not code:
            await manager.send_message(task_id, {
                "type": "error",
                "data": {"error_message": "代码内容不能为空"}
            })
            return

        # 构建初始状态
        from app.graph.state import StateFactory
        initial_state = StateFactory.create_global_state(
            task_id=task_id,
            user_id="default_user",  # TODO: 从认证系统获取
            code=code,
            language=language,
            optimization_level=optimization_level
        )

        # 创建服务实例
        from app.api.deps import get_graph_manager, get_config
        graph_manager = get_graph_manager()
        settings = get_config()
        service = WeaverService(graph_manager=graph_manager, settings=settings)

        # 发送任务开始消息
        await manager.send_message(task_id, {
            "type": "task_started",
            "data": {
                "task_id": task_id,
                "status": TaskStatus.ANALYZING.value
            }
        })

        # 流式执行任务
        async for event in service.stream_task(task_id, initial_state):
            # 发送状态更新
            await manager.send_message(task_id, event)

            # 检查是否需要人工干预
            if event.get("type") == "human_intervention_required":
                logger.info(f"任务需要人工干预: {task_id}")
                # 等待用户决策，不继续执行

        # 发送任务完成消息
        await manager.send_message(task_id, {
            "type": "task_completed",
            "data": {
                "task_id": task_id,
                "status": TaskStatus.COMPLETED.value
            }
        })

    except Exception as e:
        logger.error(f"启动任务失败: {task_id}, 错误: {str(e)}")
        await manager.send_message(task_id, {
            "type": "error",
            "data": {"error_message": f"启动任务失败: {str(e)}"}
        })


async def handle_human_decision(task_id: str, data: Dict[str, Any], websocket: WebSocket):
    """
    处理人工决策消息

    Args:
        task_id: 任务ID
        data: 消息数据
        websocket: WebSocket 连接
    """
    try:
        # 提取决策数据
        decision_data = data.get("data", {})

        # 创建服务实例
        from app.api.deps import get_graph_manager, get_config
        graph_manager = get_graph_manager()
        settings = get_config()
        service = WeaverService(graph_manager=graph_manager, settings=settings)

        # 恢复任务
        final_state = await service.resume_task(task_id, decision_data)

        # 发送恢复成功消息
        await manager.send_message(task_id, {
            "type": "task_resumed",
            "data": {
                "task_id": task_id,
                "status": final_state.get("status").value
            }
        })

        # 继续流式执行
        async for event in service.stream_task(task_id, final_state):
            await manager.send_message(task_id, event)

    except Exception as e:
        logger.error(f"处理人工决策失败: {task_id}, 错误: {str(e)}")
        await manager.send_message(task_id, {
            "type": "error",
            "data": {"error_message": f"处理人工决策失败: {str(e)}"}
        })


async def handle_cancel_task(task_id: str, websocket: WebSocket):
    """
    处理取消任务消息

    Args:
        task_id: 任务ID
        websocket: WebSocket 连接
    """
    try:
        # 创建服务实例
        from app.api.deps import get_graph_manager, get_config
        graph_manager = get_graph_manager()
        settings = get_config()
        service = WeaverService(graph_manager=graph_manager, settings=settings)

        # 取消任务
        user_input = {"action": "cancel"}
        await service.resume_task(task_id, user_input)

        # 发送取消成功消息
        await manager.send_message(task_id, {
            "type": "task_canceled",
            "data": {
                "task_id": task_id,
                "status": TaskStatus.CANCELED.value
            }
        })

    except Exception as e:
        logger.error(f"取消任务失败: {task_id}, 错误: {str(e)}")
        await manager.send_message(task_id, {
            "type": "error",
            "data": {"error_message": f"取消任务失败: {str(e)}"}
        })


# ============================================================================
# 连接状态查询
# ============================================================================

@router.get("/ws/connections")
async def get_active_connections() -> Dict[str, Any]:
    """
    获取活跃连接数

    Returns:
        Dict[str, Any]: 连接信息
    """
    return {
        "active_connections": len(manager.active_connections),
        "task_ids": list(manager.active_connections.keys())
    }
