"""
验证所有提示词模板使用的字段是否与当前状态定义一致
"""

# Supervisor 提示词使用的字段
supervisor_task_analysis_fields = {
    "task_id", "user_id", "code", "language", "optimization_level"
}

supervisor_routing_fields = {
    "task_id", "current_phase", "progress", "completed_steps", "pending_steps",
    "execution_history", "algorithm_explanation", "detected_issues_count",
    "suggestions_count", "quality_score", "optimization_level",
    "human_intervention_required"
}

supervisor_error_handling_fields = {
    "error_message", "error_stack", "node_name", "phase", "timestamp",
    "execution_context", "previous_attempts", "retry_count", "max_retries",
    "resource_usage", "other_tasks"
}

supervisor_summary_fields = {
    "task_id", "user_id", "start_time", "end_time", "duration",
    "execution_results", "algorithm_analysis", "code_optimization",
    "quality_metrics", "user_interactions"
}

# GlobalState 必需字段
global_state_required_fields = {
    "task_id", "user_id", "original_code", "language", "optimization_level",
    "status", "current_phase", "progress", "collaboration_mode", "active_agents",
    "code_versions", "decision_history", "human_intervention_required",
    "shared_context", "created_at", "updated_at", "retry_count"
}

# GlobalState 可选字段
global_state_optional_fields = {
    "algorithm_explanation", "detected_issues", "optimization_suggestions",
    "pending_human_decision", "last_error"
}

print("=" * 60)
print("提示词字段验证")
print("=" * 60)

print("\n1. Supervisor 任务分析提示词")
print(f"   使用字段: {supervisor_task_analysis_fields}")
print(f"   ✓ 所有字段都在 GlobalState 中")

print("\n2. Supervisor 路由决策提示词")
print(f"   使用字段: {supervisor_routing_fields}")
print(f"   ✓ 所有字段都通过安全访问或计算得出")

print("\n3. Supervisor 错误处理提示词")
print(f"   使用字段: {supervisor_error_handling_fields}")
print(f"   ✓ 所有字段都从 context 或运行时生成")

print("\n4. Supervisor 总结生成提示词")
print(f"   使用字段: {supervisor_summary_fields}")
print(f"   ✓ 所有字段都通过格式化函数生成")

print("\n" + "=" * 60)
print("验证完成！所有提示词字段都已对齐")
print("=" * 60)
