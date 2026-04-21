"""
全局配置管理模块

使用 Pydantic Settings 进行环境变量读取和配置验证
支持开发、测试、生产环境的配置管理
"""
import sys
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用全局配置类"""
    
    # 应用基础配置
    app_name: str = Field(default="AlgoWeaver AI", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    environment: str = Field(default="development", description="运行环境")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器主机地址")
    port: int = Field(default=8000, description="服务器端口")
    reload: bool = Field(default=True, description="热重载模式")
    
    # LLM API 配置
    llm_api_key: str = Field(..., description="LLM API 密钥")
    llm_api_base: Optional[str] = Field(default=None, description="LLM API 基础URL")
    llm_model: str = Field(default="gpt-4", description="默认LLM模型")
    llm_temperature: float = Field(default=0.7, description="LLM 温度参数")
    llm_max_tokens: int = Field(default=4096, description="LLM 最大令牌数")
    
    # LangSmith 追踪配置
    langsmith_api_key: Optional[str] = Field(default=None, description="LangSmith API 密钥")
    langsmith_project: str = Field(default="algoweaver-ai", description="LangSmith 项目名称")
    langsmith_endpoint: str = Field(default="https://api.smith.langchain.com", description="LangSmith 端点")
    langsmith_tracing: bool = Field(default=True, description="启用 LangSmith 追踪")
    
    # Redis 缓存配置
    redis_host: str = Field(default="localhost", description="Redis 主机地址")
    redis_port: int = Field(default=6379, description="Redis 端口")
    redis_password: Optional[str] = Field(default=None, description="Redis 密码")
    redis_db: int = Field(default=0, description="Redis 数据库编号")
    redis_max_connections: int = Field(default=20, description="Redis 最大连接数")
    
    # 安全配置
    secret_key: str = Field(..., description="应用密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT 算法")
    jwt_expire_hours: int = Field(default=24, description="JWT 过期时间(小时)")
    
    # CORS 配置
    cors_origins: List[str] = Field(default=["http://localhost:3000"], description="允许的跨域源")
    cors_allow_credentials: bool = Field(default=True, description="允许跨域凭证")
    
    # Python 沙箱配置
    sandbox_timeout: int = Field(default=30, description="沙箱执行超时时间(秒)")
    sandbox_memory_limit: str = Field(default="128m", description="沙箱内存限制")
    sandbox_cpu_quota: int = Field(default=50000, description="沙箱CPU配额")
    sandbox_max_processes: int = Field(default=50, description="沙箱最大进程数")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    log_file: Optional[str] = Field(default=None, description="日志文件路径")
    log_max_size: int = Field(default=10485760, description="日志文件最大大小(字节)")  # 10MB
    log_backup_count: int = Field(default=5, description="日志文件备份数量")
    
    # 性能配置
    max_concurrent_tasks: int = Field(default=10, description="最大并发任务数")
    task_timeout: int = Field(default=300, description="任务超时时间(秒)")
    rate_limit_per_hour: int = Field(default=100, description="每小时请求限制")

    class Config:
        env_file = ".env.dev"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # 允许额外字段

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """验证运行环境"""
        allowed_envs = ["development", "testing", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"环境必须是以下之一: {allowed_envs}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """验证日志级别"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"日志级别必须是以下之一: {allowed_levels}")
        return v.upper()

    @field_validator("llm_temperature")
    @classmethod
    def validate_temperature(cls, v):
        """验证LLM温度参数"""
        if not 0.0 <= v <= 2.0:
            raise ValueError("LLM温度参数必须在0.0到2.0之间")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        """验证端口号"""
        if not 1 <= v <= 65535:
            raise ValueError("端口号必须在1到65535之间")
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v):
        """验证CORS源"""
        if not v:
            raise ValueError("至少需要配置一个CORS源")
        return v
    
    @property
    def redis_url(self) -> str:
        """构建Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        """判断是否为测试环境"""
        return self.environment == "testing"


@lru_cache()
def get_settings() -> Settings:
    """
    获取应用配置实例
    
    使用 lru_cache 确保配置单例，避免重复读取环境变量
    
    Returns:
        Settings: 配置实例
    """
    return Settings()


# 全局配置实例
settings = get_settings()


def reload_settings() -> Settings:
    """
    重新加载配置
    
    清除缓存并重新读取环境变量，用于配置热重载
    
    Returns:
        Settings: 新的配置实例
    """
    get_settings.cache_clear()
    global settings
    settings = get_settings()
    return settings


def validate_required_settings():
    """
    验证必需的配置项
    
    在应用启动时调用，确保关键配置项已正确设置
    
    Raises:
        ValueError: 当必需配置项缺失时抛出异常
    """
    required_settings = [
        ("llm_api_key", "LLM API 密钥"),
        ("secret_key", "应用密钥"),
    ]
    
    missing_settings = []
    for setting_name, display_name in required_settings:
        if not getattr(settings, setting_name, None):
            missing_settings.append(display_name)
    
    if missing_settings:
        raise ValueError(f"缺少必需的配置项: {', '.join(missing_settings)}")


def get_environment_info() -> dict:
    """
    获取环境信息
    
    Returns:
        dict: 包含环境信息的字典
    """
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "python_version": sys.version,
        "langsmith_tracing": settings.langsmith_tracing,
    }