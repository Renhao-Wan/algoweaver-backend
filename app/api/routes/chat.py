"""
核心 API 路由模块

提供代码分析和优化的核心 API 接口。
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse

from app.schemas.requests import TaskRequest, HumanInterventionRequest, ReportGenerationRequest
from app.schemas.responses import (
    TaskCreationResponse,
    TaskStatusResponse,
    AnalysisResultResponse,
    ReportResponse
)
from app.services.weaver_service import WeaverService
from app.api.deps import get_graph_manager, get_config
from app.graph.main_graph import MainGraphManager
from app.core.config import Settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api", tags=["chat"])


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
# API 路由
# ============================================================================

@router.post(
    "/weave-algorithm",
    response_model=TaskCreationResponse,
    summary="创建代码分析任务",
    description="提交代码进行分析和优化，返回任务ID和WebSocket连接URL"
)
async def weave_algorithm(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    service: WeaverService = Depends(get_weaver_service)
) -> TaskCreationResponse:
    """
    创建代码分析任务

    Args:
        request: 任务请求
        background_tasks: 后台任务
        service: Weaver Service

    Returns:
        TaskCreationResponse: 任务创建响应
    """
    try:
        logger.info(f"收到代码分析请求: language={request.language}, optimization_level={request.optimization_level}")

        # 创建任务
        response = await service.create_task(request)

        # 构建初始状态
        from app.graph.state import StateFactory
        initial_state = StateFactory.create_global_state(
            task_id=response.task_id,
            user_id="default_user",  # TODO: 从认证系统获取
            code=request.code,
            language=request.language.value,
            optimization_level=request.optimization_level.value
        )

        # 在后台执行任务
        background_tasks.add_task(
            service.execute_task,
            response.task_id,
            initial_state
        )

        logger.info(f"任务创建成功: {response.task_id}")
        return response

    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"任务创建失败: {str(e)}"
        )


@router.get(
    "/task/{task_id}/status",
    response_model=TaskStatusResponse,
    summary="查询任务状态",
    description="根据任务ID查询任务执行状态和进度"
)
async def get_task_status(
    task_id: str,
    include_details: bool = True,
    include_logs: bool = False,
    service: WeaverService = Depends(get_weaver_service)
) -> TaskStatusResponse:
    """
    查询任务状态

    Args:
        task_id: 任务ID
        include_details: 是否包含详细信息
        include_logs: 是否包含执行日志
        service: Weaver Service

    Returns:
        TaskStatusResponse: 任务状态响应
    """
    try:
        logger.info(f"查询任务状态: {task_id}")

        # 查询状态
        response = await service.get_task_status(task_id)

        # 根据参数过滤响应内容
        if not include_details:
            response.result = None

        if not include_logs:
            response.logs = None

        return response

    except Exception as e:
        logger.error(f"查询任务状态失败: {task_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询任务状态失败: {str(e)}"
        )


@router.get(
    "/task/{task_id}/result",
    response_model=AnalysisResultResponse,
    summary="获取分析结果",
    description="获取任务的完整分析结果，包括算法讲解、问题检测和优化建议"
)
async def get_analysis_result(
    task_id: str,
    service: WeaverService = Depends(get_weaver_service)
) -> AnalysisResultResponse:
    """
    获取分析结果

    Args:
        task_id: 任务ID
        service: Weaver Service

    Returns:
        AnalysisResultResponse: 分析结果响应
    """
    try:
        logger.info(f"获取分析结果: {task_id}")

        # 获取结果
        response = await service.get_analysis_result(task_id)

        return response

    except ValueError as e:
        logger.warning(f"任务不存在: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取分析结果失败: {task_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分析结果失败: {str(e)}"
        )


@router.post(
    "/task/{task_id}/resume",
    response_model=TaskStatusResponse,
    summary="恢复暂停的任务",
    description="提供用户决策，恢复因 Human-in-the-loop 暂停的任务"
)
async def resume_task(
    task_id: str,
    intervention: HumanInterventionRequest,
    service: WeaverService = Depends(get_weaver_service)
) -> TaskStatusResponse:
    """
    恢复暂停的任务

    Args:
        task_id: 任务ID
        intervention: 人工干预请求
        service: Weaver Service

    Returns:
        TaskStatusResponse: 任务状态响应
    """
    try:
        logger.info(f"恢复任务: {task_id}")

        # 构建用户输入
        user_input = {
            "action": "continue",
            "accepted_suggestions": intervention.accepted_suggestions,
            "rejected_suggestions": intervention.rejected_suggestions,
            "custom_input": intervention.custom_input
        }

        # 恢复任务
        final_state = await service.resume_task(task_id, user_input)

        # 构建响应
        return TaskStatusResponse(
            success=True,
            message="任务已恢复",
            task_id=task_id,
            status=final_state.get("status"),
            progress_percent=int(final_state.get("progress", 0) * 100),
            current_phase=final_state.get("current_phase").value,
            created_at=final_state.get("created_at"),
            updated_at=final_state.get("updated_at")
        )

    except Exception as e:
        logger.error(f"恢复任务失败: {task_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复任务失败: {str(e)}"
        )


@router.delete(
    "/task/{task_id}",
    summary="取消任务",
    description="取消正在执行的任务"
)
async def cancel_task(
    task_id: str,
    service: WeaverService = Depends(get_weaver_service)
) -> JSONResponse:
    """
    取消任务

    Args:
        task_id: 任务ID
        service: Weaver Service

    Returns:
        JSONResponse: 响应
    """
    try:
        logger.info(f"取消任务: {task_id}")

        # 构建取消输入
        user_input = {"action": "cancel"}

        # 恢复任务并取消
        await service.resume_task(task_id, user_input)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "任务已取消",
                "task_id": task_id
            }
        )

    except Exception as e:
        logger.error(f"取消任务失败: {task_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消任务失败: {str(e)}"
        )


# ============================================================================
# 报告生成
# ============================================================================

@router.post(
    "/task/{task_id}/report",
    response_model=ReportResponse,
    summary="生成教学报告",
    description="为指定任务生成教学报告"
)
async def generate_report(
    task_id: str,
    request: Optional[ReportGenerationRequest] = None,
    service: WeaverService = Depends(get_weaver_service)
) -> ReportResponse:
    """
    生成教学报告

    Args:
        task_id: 任务ID
        request: 报告生成请求
        service: Weaver Service

    Returns:
        ReportResponse: 报告响应
    """
    try:
        logger.info(f"生成教学报告: {task_id}")

        # 生成报告
        response = await service.generate_report(task_id, request)

        return response

    except ValueError as e:
        logger.warning(f"任务不存在: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"生成报告失败: {task_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成报告失败: {str(e)}"
        )


@router.get(
    "/task/{task_id}/report/content",
    response_class=PlainTextResponse,
    summary="获取报告内容",
    description="直接获取报告内容（不保存文件）"
)
async def get_report_content(
    task_id: str,
    format: str = "markdown",
    template: str = "default",
    include_history: bool = True,
    service: WeaverService = Depends(get_weaver_service)
) -> str:
    """
    获取报告内容

    Args:
        task_id: 任务ID
        format: 报告格式
        template: 报告模板
        include_history: 是否包含优化历史
        service: Weaver Service

    Returns:
        str: 报告内容
    """
    try:
        logger.info(f"获取报告内容: {task_id}")

        # 获取报告内容
        content = await service.get_report_content(
            task_id,
            format=format,
            template=template,
            include_history=include_history
        )

        return content

    except ValueError as e:
        logger.warning(f"任务不存在: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取报告内容失败: {task_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取报告内容失败: {str(e)}"
        )


# ============================================================================
# 健康检查
# ============================================================================

@router.get(
    "/health",
    summary="健康检查",
    description="检查服务健康状态"
)
async def health_check() -> JSONResponse:
    """
    健康检查

    Returns:
        JSONResponse: 健康状态
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "AlgoWeaver AI",
            "version": "1.0.0"
        }
    )

