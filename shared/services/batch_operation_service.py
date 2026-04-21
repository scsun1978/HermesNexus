"""
HermesNexus v1.2 - 批量操作服务
处理资产和任务的批量操作
"""

import asyncio
import copy
import uuid
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone
from collections import defaultdict
import logging

from shared.models.batch_operations import (
    BatchOperationStatus,
    BatchItemResult,
    BatchOperationSummary,
    BatchOperationResponse,
    AssetBatchCreateRequest,
    AssetBatchUpdateRequest,
    AssetBatchDeleteRequest,
    TaskBatchCreateRequest,
    TaskBatchDispatchRequest,
    IdempotencyResult,
    BatchRetryPolicy,
    BatchPartialFailureHandling,
)

logger = logging.getLogger(__name__)

# 性能配置常量
MAX_ASSETS_BATCH_SIZE = 100  # 资产批量操作最大数量
MAX_TASKS_BATCH_SIZE = 50  # 任务批量操作最大数量
MAX_PARALLEL_TASKS = 10  # 最大并行任务数
PERFORMANCE_LOG_THRESHOLD = 1.0  # 性能日志阈值（秒）


class BatchOperationService:
    """批量操作服务"""

    def __init__(self, database=None, audit_service=None):
        """
        初始化批量操作服务

        Args:
            database: 数据库实例
            audit_service: 审计服务实例（可选）
        """
        self.database = database
        self._idempotency_cache = {}  # 幂等性缓存
        self._operation_history = {}  # 操作历史记录

        # 审计服务（延迟导入避免循环依赖）
        self._audit_service = audit_service
        if self._audit_service is None:
            try:
                from shared.services.batch_audit_service import get_batch_audit_service

                self._audit_service = get_batch_audit_service()
            except ImportError:
                logger.warning("审计服务不可用，批量操作将不会被记录")
                self._audit_service = None

    def _build_audit_parameters(
        self, request: Any, extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """构建审计参数快照"""
        parameters: Dict[str, Any] = {}
        if hasattr(request, "model_dump"):
            parameters = request.model_dump(exclude_none=True)
        elif hasattr(request, "dict"):
            parameters = request.dict(exclude_none=True)
        elif isinstance(request, dict):
            parameters = {k: v for k, v in request.items() if v is not None}

        if extra:
            parameters.update({k: v for k, v in extra.items() if v is not None})

        # 审计记录中不重复保留原始响应字段
        for sensitive_key in ("idempotency_key",):
            parameters.pop(sensitive_key, None)

        return parameters

    def _capture_asset_snapshots(self, asset_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """捕获资产当前状态，用于失败回滚"""
        snapshots: Dict[str, Optional[Dict[str, Any]]] = {}
        if not self.database or not hasattr(self.database, "get_device"):
            return snapshots

        for asset_id in asset_ids:
            try:
                snapshots[asset_id] = copy.deepcopy(self.database.get_device(asset_id))
            except Exception:
                snapshots[asset_id] = None

        return snapshots

    def _restore_asset_snapshots(self, snapshots: Dict[str, Optional[Dict[str, Any]]]) -> None:
        """恢复资产到捕获时的状态"""
        if not snapshots or not self.database:
            return

        if hasattr(self.database, "lock") and hasattr(self.database, "devices"):
            with self.database.lock:
                for asset_id, original_data in snapshots.items():
                    if original_data is None:
                        self.database.devices.pop(asset_id, None)
                    else:
                        self.database.devices[asset_id] = copy.deepcopy(original_data)
            return

        for asset_id, original_data in snapshots.items():
            if original_data is None:
                if hasattr(self.database, "delete_device"):
                    try:
                        self.database.delete_device(asset_id)
                    except Exception:
                        pass
                continue

            if hasattr(self.database, "get_device") and hasattr(self.database, "update_device"):
                current_data = self.database.get_device(asset_id)
                if isinstance(current_data, dict):
                    current_data.clear()
                    current_data.update(copy.deepcopy(original_data))

    def _schedule_batch_audit(
        self, response: Any, request: Any, extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """异步记录批量操作审计"""
        if not self._audit_service:
            return

        try:
            asyncio.create_task(
                self._audit_service.log_batch_operation(
                    operation=response,
                    user_id=(
                        request.get("user_id")
                        if isinstance(request, dict)
                        else getattr(request, "user_id", None)
                    ),
                    username=(
                        request.get("username")
                        if isinstance(request, dict)
                        else getattr(request, "username", None)
                    ),
                    request_ip=(
                        request.get("request_ip")
                        if isinstance(request, dict)
                        else getattr(request, "request_ip", None)
                    ),
                    user_agent=(
                        request.get("user_agent")
                        if isinstance(request, dict)
                        else getattr(request, "user_agent", None)
                    ),
                    parameters=self._build_audit_parameters(request, extra),
                )
            )
        except Exception as audit_error:
            logger.warning(f"记录审计日志失败: {audit_error}")

    async def create_assets_batch(self, request: AssetBatchCreateRequest) -> BatchOperationResponse:
        """
        批量创建资产

        Args:
            request: 批量创建请求

        Returns:
            批量操作响应
        """
        operation_id = f"asset-batch-{uuid.uuid4().hex[:8]}"

        # 批量大小验证
        if len(request.assets) > MAX_ASSETS_BATCH_SIZE:
            response = BatchOperationResponse(
                operation_id=operation_id,
                operation_type="asset_create",
                status=BatchOperationStatus.FAILED,
                summary=BatchOperationSummary(
                    total_items=len(request.assets),
                    successful_items=0,
                    failed_items=len(request.assets),
                    operation_id=operation_id,
                ),
                results=[],
                started_at=datetime.now(timezone.utc),
                error_summary={"validation_error": len(request.assets)},
            )
            self._schedule_batch_audit(response, request)
            return response

        logger.info(f"🚀 开始批量创建资产: operation_id={operation_id}, items={len(request.assets)}")

        # 检查幂等性
        if request.idempotency_key:
            idempotency_result = self._check_idempotency(request.idempotency_key, "asset_create")
            if idempotency_result.is_idempotent:
                logger.info(f"✅ 幂等性命中: {request.idempotency_key}")
                return idempotency_result.cached_result

        # 仅验证模式
        if request.validate_only:
            response = await _validate_assets_batch(request.assets, operation_id)
            self._schedule_batch_audit(response, request, {"validate_only": True})
            return response

        # 执行批量创建（优化版）
        results = []
        successful_count = 0
        failed_count = 0
        error_summary = defaultdict(int)

        started_at = datetime.now(timezone.utc)
        start_time = time.time()  # 性能监控开始时间

        # 预校验阶段：批量校验所有资产数据
        valid_assets = {}
        validation_errors = []
        seen_asset_ids = set()  # 用于检测重复ID

        # 如果要求遇错停止，需要逐个处理而非批量校验
        if request.stop_on_first_error:
            # 逐个校验和处理，遇错即止
            for i, asset_data in enumerate(request.assets):
                try:
                    # 检查重复ID
                    asset_id = asset_data.get("asset_id", f"unknown-{i}")
                    if asset_id in seen_asset_ids:
                        error_msg = f"重复的资产ID: {asset_id}"
                        error_type = "duplicate_error"

                        error_summary[error_type] += 1
                        failed_count += 1

                        item_result = BatchItemResult(
                            id=asset_id,
                            success=False,
                            message=error_msg,
                            error_code=error_type,
                        )
                        results.append(item_result)

                        logger.warning(f"⚠️ 遇到重复ID，停止处理: {error_msg}")
                        break

                    seen_asset_ids.add(asset_id)

                    # 校验资产数据
                    validation_result = _validate_asset_data(asset_data)
                    if not validation_result["valid"]:
                        error_msg = validation_result["error"]
                        error_type = "validation_error"

                        error_summary[error_type] += 1
                        failed_count += 1

                        item_result = BatchItemResult(
                            id=asset_id,
                            success=False,
                            message=f"资产数据校验失败: {error_msg}",
                            error_code=error_type,
                        )
                        results.append(item_result)

                        logger.warning(f"⚠️ 遇到校验错误，停止处理: {error_msg}")
                        break

                    # 处理资产创建
                    result = await _create_single_asset(asset_data, self.database)
                    successful_count += 1
                    item_result = BatchItemResult(
                        id=asset_id, success=True, message="资产创建成功", data=result
                    )
                    results.append(item_result)

                except Exception as e:
                    error_msg = str(e)
                    error_type = _classify_error(error_msg)
                    error_summary[error_type] += 1
                    failed_count += 1

                    item_result = BatchItemResult(
                        id=asset_data.get("asset_id", f"unknown-{i}"),
                        success=False,
                        message=f"资产创建失败: {error_msg}",
                        error_code=error_type,
                    )
                    results.append(item_result)

                    logger.warning(f"⚠️ 遇到错误，停止处理: {error_msg}")
                    break
        else:
            # 遇错继续：批量校验所有资产数据
            for i, asset_data in enumerate(request.assets):
                validation_result = _validate_asset_data(asset_data)
                if not validation_result["valid"]:
                    error_msg = validation_result["error"]
                    error_type = "validation_error"

                    error_summary[error_type] += 1
                    failed_count += 1

                    validation_errors.append(
                        {
                            "index": i,
                            "asset_id": asset_data.get("asset_id", f"unknown-{i}"),
                            "error": error_msg,
                            "error_type": error_type,
                        }
                    )

                else:
                    asset_id = asset_data.get("asset_id", f"unknown-{i}")

                    # 检测重复ID
                    if asset_id in seen_asset_ids:
                        error_msg = f"重复的资产ID: {asset_id}"
                        error_type = "duplicate_error"

                        error_summary[error_type] += 1
                        failed_count += 1

                        validation_errors.append(
                            {
                                "index": i,
                                "asset_id": asset_id,
                                "error": error_msg,
                                "error_type": error_type,
                            }
                        )
                    else:
                        seen_asset_ids.add(asset_id)
                        valid_assets[asset_id] = asset_data

            # 处理校验错误结果
            for error_info in validation_errors:
                item_result = BatchItemResult(
                    id=error_info["asset_id"],
                    success=False,
                    message=f"资产数据校验失败: {error_info['error']}",
                    error_code=error_info["error_type"],
                )
                results.append(item_result)

        # 批量创建阶段：使用批量数据库操作
        if valid_assets and not (request.stop_on_first_error and validation_errors):
            original_asset_snapshots = self._capture_asset_snapshots(list(valid_assets.keys()))
            try:
                # 如果要求遇错停止，使用逐个创建而非批量创建
                if request.stop_on_first_error:
                    # 逐个创建，遇错即止
                    for asset_id, asset_data in valid_assets.items():
                        try:
                            result = await _create_single_asset(asset_data, self.database)
                            successful_count += 1
                            item_result = BatchItemResult(
                                id=asset_id,
                                success=True,
                                message="资产创建成功",
                                data=result,
                            )
                            results.append(item_result)
                        except Exception as single_error:
                            failed_count += 1
                            error_type = _classify_error(str(single_error))
                            error_summary[error_type] += 1
                            item_result = BatchItemResult(
                                id=asset_id,
                                success=False,
                                message=f"资产创建失败: {str(single_error)}",
                                error_code=error_type,
                            )
                            results.append(item_result)
                            # 遇错停止
                            logger.warning(f"⚠️ 遇到创建错误，停止处理: {str(single_error)}")
                            break
                else:
                    # 使用批量数据库操作替代逐个操作
                    batch_results = await _create_assets_batch(valid_assets, self.database)

                    for asset_id, success in batch_results.items():
                        if success:
                            successful_count += 1
                            item_result = BatchItemResult(
                                id=asset_id,
                                success=True,
                                message="资产创建成功",
                                data={"asset_id": asset_id},
                            )
                            results.append(item_result)
                        else:
                            failed_count += 1
                            error_summary["unknown_error"] += 1
                            item_result = BatchItemResult(
                                id=asset_id,
                                success=False,
                                message="资产创建失败",
                                error_code="unknown_error",
                            )
                            results.append(item_result)

            except Exception as e:
                # 批量操作失败时的回退处理
                logger.error(f"批量创建失败，回退到逐个处理: {str(e)}")
                self._restore_asset_snapshots(original_asset_snapshots)
                for asset_id, asset_data in valid_assets.items():
                    try:
                        result = await _create_single_asset(asset_data, self.database)
                        successful_count += 1
                        item_result = BatchItemResult(
                            id=asset_id,
                            success=True,
                            message="资产创建成功",
                            data=result,
                        )
                        results.append(item_result)
                    except Exception as single_error:
                        failed_count += 1
                        error_type = _classify_error(str(single_error))
                        error_summary[error_type] += 1
                        item_result = BatchItemResult(
                            id=asset_id,
                            success=False,
                            message=f"资产创建失败: {str(single_error)}",
                            error_code=error_type,
                        )
                        results.append(item_result)

                    if request.stop_on_first_error:
                        break

        # 构建响应
        completed_at = datetime.now(timezone.utc)
        elapsed_time = time.time() - start_time  # 计算耗时
        total_items = len(request.assets)
        success_rate = (successful_count / total_items * 100) if total_items > 0 else 0.0

        # 性能监控日志
        if elapsed_time > PERFORMANCE_LOG_THRESHOLD:
            logger.info(
                f"⚡ 批量操作性能: operation_id={operation_id}, "
                f"items={total_items}, time={elapsed_time:.2f}s, "
                f"rate={total_items/elapsed_time:.1f} items/s"
            )

        status = BatchOperationStatus.COMPLETED
        if failed_count > 0 and successful_count > 0:
            status = BatchOperationStatus.PARTIAL_SUCCESS
        elif failed_count > 0 and successful_count == 0:
            status = BatchOperationStatus.FAILED

        response = BatchOperationResponse(
            operation_id=operation_id,
            operation_type="asset_create",
            status=status,
            summary=BatchOperationSummary(
                total_items=total_items,
                successful_items=successful_count,
                failed_items=failed_count,
                skipped_items=0,
                success_rate=success_rate,
                operation_id=operation_id,
            ),
            results=results,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=dict(error_summary),
        )

        # 缓存幂等性结果
        if request.idempotency_key:
            self._save_idempotency_result(request.idempotency_key, response)

        # 记录操作历史
        self._operation_history[operation_id] = response

        logger.info(f"✅ 批量创建资产完成: 成功={successful_count}, 失败={failed_count}")

        # 记录审计日志（异步，不影响操作性能）
        self._schedule_batch_audit(response, request)

        return response

    async def update_assets_batch(self, request: AssetBatchUpdateRequest) -> BatchOperationResponse:
        """
        批量更新资产

        Args:
            request: 批量更新请求

        Returns:
            批量操作响应
        """
        operation_id = f"asset-update-batch-{uuid.uuid4().hex[:8]}"

        # 批量大小验证
        if len(request.asset_ids) > MAX_ASSETS_BATCH_SIZE:
            response = BatchOperationResponse(
                operation_id=operation_id,
                operation_type="asset_update",
                status=BatchOperationStatus.FAILED,
                summary=BatchOperationSummary(
                    total_items=len(request.asset_ids),
                    successful_items=0,
                    failed_items=len(request.asset_ids),
                    operation_id=operation_id,
                ),
                results=[],
                started_at=datetime.now(timezone.utc),
                error_summary={"validation_error": len(request.asset_ids)},
            )
            self._schedule_batch_audit(response, request)
            return response

        logger.info(f"🔄 开始批量更新资产: operation_id={operation_id}, items={len(request.asset_ids)}")

        # 检查幂等性
        if request.idempotency_key:
            idempotency_result = self._check_idempotency(request.idempotency_key, "asset_update")
            if idempotency_result.is_idempotent:
                logger.info(f"✅ 幂等性命中: {request.idempotency_key}")
                return idempotency_result.cached_result

        # 仅验证模式
        if request.validate_only:
            response = await _validate_assets_update_batch(
                request.asset_ids, request.updates, operation_id
            )
            self._schedule_batch_audit(response, request, {"validate_only": True})
            return response

        # 执行批量更新（优化版）
        results = []
        successful_count = 0
        failed_count = 0
        error_summary = defaultdict(int)

        started_at = datetime.now(timezone.utc)
        start_time = time.time()  # 性能监控开始时间
        original_asset_snapshots = self._capture_asset_snapshots(request.asset_ids)

        try:
            # 批量更新阶段：使用批量数据库操作
            if request.stop_on_first_error:
                # 逐个更新，遇错即止
                for asset_id in request.asset_ids:
                    try:
                        result = await _update_single_asset(
                            asset_id, request.updates, self.database
                        )
                        successful_count += 1
                        item_result = BatchItemResult(
                            id=asset_id,
                            success=True,
                            message="资产更新成功",
                            data=result,
                        )
                        results.append(item_result)
                    except Exception as single_error:
                        failed_count += 1
                        error_type = _classify_error(str(single_error))
                        error_summary[error_type] += 1
                        item_result = BatchItemResult(
                            id=asset_id,
                            success=False,
                            message=f"资产更新失败: {str(single_error)}",
                            error_code=error_type,
                        )
                        results.append(item_result)
                        # 遇错停止
                        logger.warning(f"⚠️ 遇到更新错误，停止处理: {str(single_error)}")
                        break
            else:
                # 使用批量数据库操作（带回滚机制）
                updates_dict = {asset_id: request.updates for asset_id in request.asset_ids}
                batch_results = await _update_assets_batch_with_rollback(
                    updates_dict, self.database
                )

                for asset_id, success in batch_results.items():
                    if success:
                        successful_count += 1
                        item_result = BatchItemResult(
                            id=asset_id,
                            success=True,
                            message="资产更新成功",
                            data={"asset_id": asset_id},
                        )
                        results.append(item_result)
                    else:
                        failed_count += 1
                        error_summary["not_found_error"] += 1
                        item_result = BatchItemResult(
                            id=asset_id,
                            success=False,
                            message="资产不存在或更新失败",
                            error_code="not_found_error",
                        )
                        results.append(item_result)

                    # 遇到错误时停止（针对stop_on_first_error）
                    if not success and request.stop_on_first_error:
                        break

        except Exception as e:
            # 批量操作失败时的回退处理
            logger.error(f"批量更新失败，回退到逐个处理: {str(e)}")

            # 先恢复批量操作开始前的状态，再进行逐个处理
            self._restore_asset_snapshots(original_asset_snapshots)

            # 逐个处理
            for asset_id in request.asset_ids:
                try:
                    result = await _update_single_asset(asset_id, request.updates, self.database)
                    successful_count += 1
                    item_result = BatchItemResult(
                        id=asset_id, success=True, message="资产更新成功", data=result
                    )
                    results.append(item_result)
                except Exception as single_error:
                    failed_count += 1
                    error_type = _classify_error(str(single_error))
                    error_summary[error_type] += 1
                    item_result = BatchItemResult(
                        id=asset_id,
                        success=False,
                        message=f"资产更新失败: {str(single_error)}",
                        error_code=error_type,
                    )
                    results.append(item_result)

                    if request.stop_on_first_error:
                        logger.warning(f"⚠️ 遇到更新错误，停止处理: {str(single_error)}")
                        break

        # 构建响应
        completed_at = datetime.now(timezone.utc)
        elapsed_time = time.time() - start_time  # 计算耗时
        total_items = len(request.asset_ids)
        success_rate = (successful_count / total_items * 100) if total_items > 0 else 0.0

        # 性能监控日志
        if elapsed_time > PERFORMANCE_LOG_THRESHOLD:
            logger.info(
                f"⚡ 批量更新性能: operation_id={operation_id}, "
                f"items={total_items}, time={elapsed_time:.2f}s, "
                f"rate={total_items/elapsed_time:.1f} items/s"
            )

        status = BatchOperationStatus.COMPLETED
        if failed_count > 0 and successful_count > 0:
            status = BatchOperationStatus.PARTIAL_SUCCESS
        elif failed_count > 0 and successful_count == 0:
            status = BatchOperationStatus.FAILED

        response = BatchOperationResponse(
            operation_id=operation_id,
            operation_type="asset_update",
            status=status,
            summary=BatchOperationSummary(
                total_items=total_items,
                successful_items=successful_count,
                failed_items=failed_count,
                skipped_items=0,
                success_rate=success_rate,
                operation_id=operation_id,
            ),
            results=results,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=dict(error_summary),
        )

        # 缓存幂等性结果
        if request.idempotency_key:
            self._save_idempotency_result(request.idempotency_key, response)

        logger.info(f"✅ 批量更新资产完成: 成功={successful_count}, 失败={failed_count}")

        # 记录审计日志（异步，不影响操作性能）
        self._schedule_batch_audit(response, request)

        return response

    async def create_tasks_batch(self, request: TaskBatchCreateRequest) -> BatchOperationResponse:
        """
        批量创建任务

        Args:
            request: 批量任务创建请求

        Returns:
            批量操作响应
        """
        operation_id = f"task-batch-{uuid.uuid4().hex[:8]}"

        # 批量大小验证
        if len(request.tasks) > MAX_TASKS_BATCH_SIZE:
            response = BatchOperationResponse(
                operation_id=operation_id,
                operation_type="task_create",
                status=BatchOperationStatus.FAILED,
                summary=BatchOperationSummary(
                    total_items=len(request.tasks),
                    successful_items=0,
                    failed_items=len(request.tasks),
                    operation_id=operation_id,
                ),
                results=[],
                started_at=datetime.now(timezone.utc),
                error_summary={"validation_error": len(request.tasks)},
            )
            self._schedule_batch_audit(response, request)
            return response

        # 并行任务数限制验证
        parallel_tasks = (
            min(request.max_parallel_tasks, MAX_PARALLEL_TASKS) if request.parallel_execution else 1
        )

        logger.info(
            f"🚀 开始批量创建任务: operation_id={operation_id}, items={len(request.tasks)}, parallel={request.parallel_execution}, max_parallel={parallel_tasks}"
        )

        # 检查幂等性
        if request.idempotency_key:
            idempotency_result = self._check_idempotency(request.idempotency_key, "task_create")
            if idempotency_result.is_idempotent:
                logger.info(f"✅ 幂等性命中: {request.idempotency_key}")
                return idempotency_result.cached_result

        started_at = datetime.now(timezone.utc)

        # 根据是否并行执行选择处理方式
        if request.parallel_execution:
            results = await _create_tasks_parallel(
                request.tasks,
                parallel_tasks,  # 使用限制后的并行数量
                request.stop_on_first_error,
                operation_id,
                self.database,
            )
        else:
            results = await _create_tasks_sequential(
                request.tasks, request.stop_on_first_error, operation_id, self.database
            )

        # 统计结果
        successful_count = sum(1 for r in results if r.success)
        failed_count = sum(1 for r in results if not r.success)
        error_summary = defaultdict(int)

        for result in results:
            if not result.success and result.error_code:
                error_summary[result.error_code] += 1

        # 构建响应
        completed_at = datetime.now(timezone.utc)
        total_items = len(request.tasks)
        success_rate = (successful_count / total_items * 100) if total_items > 0 else 0.0

        status = BatchOperationStatus.COMPLETED
        if failed_count > 0 and successful_count > 0:
            status = BatchOperationStatus.PARTIAL_SUCCESS
        elif failed_count > 0 and successful_count == 0:
            status = BatchOperationStatus.FAILED

        response = BatchOperationResponse(
            operation_id=operation_id,
            operation_type="task_create",
            status=status,
            summary=BatchOperationSummary(
                total_items=total_items,
                successful_items=successful_count,
                failed_items=failed_count,
                skipped_items=0,
                success_rate=success_rate,
                operation_id=operation_id,
            ),
            results=results,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=dict(error_summary),
        )

        # 缓存幂等性结果
        if request.idempotency_key:
            self._save_idempotency_result(request.idempotency_key, response)

        logger.info(f"✅ 批量创建任务完成: 成功={successful_count}, 失败={failed_count}")

        self._schedule_batch_audit(response, request)

        return response

    async def delete_assets_batch(self, request: AssetBatchDeleteRequest) -> BatchOperationResponse:
        """
        批量删除资产

        Args:
            request: 批量删除请求

        Returns:
            批量操作响应
        """
        operation_id = f"asset-delete-batch-{uuid.uuid4().hex[:8]}"
        logger.info(f"🗑️ 开始批量删除资产: operation_id={operation_id}, items={len(request.asset_ids)}")

        # 检查幂等性
        if request.idempotency_key:
            idempotency_result = self._check_idempotency(request.idempotency_key, "asset_delete")
            if idempotency_result.is_idempotent:
                logger.info(f"✅ 幂等性命中: {request.idempotency_key}")
                return idempotency_result.cached_result

        results = []
        successful_count = 0
        failed_count = 0
        error_summary = defaultdict(int)

        started_at = datetime.now(timezone.utc)

        for asset_id in request.asset_ids:
            try:
                # 调用资产删除逻辑
                result = await _delete_single_asset(asset_id, request.force, self.database)

                item_result = BatchItemResult(
                    id=asset_id, success=True, message="资产删除成功", data=result
                )
                successful_count += 1
                results.append(item_result)

            except Exception as e:
                error_msg = str(e)
                error_type = _classify_error(error_msg)
                error_summary[error_type] += 1
                failed_count += 1

                item_result = BatchItemResult(
                    id=asset_id,
                    success=False,
                    message=f"资产删除失败: {error_msg}",
                    error_code=error_type,
                )
                results.append(item_result)

                if request.stop_on_first_error:
                    logger.warning(f"⚠️ 遇到错误，停止处理: {error_msg}")
                    break

        # 构建响应
        completed_at = datetime.now(timezone.utc)
        total_items = len(request.asset_ids)
        success_rate = (successful_count / total_items * 100) if total_items > 0 else 0.0

        status = BatchOperationStatus.COMPLETED
        if failed_count > 0 and successful_count > 0:
            status = BatchOperationStatus.PARTIAL_SUCCESS
        elif failed_count > 0 and successful_count == 0:
            status = BatchOperationStatus.FAILED

        response = BatchOperationResponse(
            operation_id=operation_id,
            operation_type="asset_delete",
            status=status,
            summary=BatchOperationSummary(
                total_items=total_items,
                successful_items=successful_count,
                failed_items=failed_count,
                skipped_items=0,
                success_rate=success_rate,
                operation_id=operation_id,
            ),
            results=results,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=dict(error_summary),
        )

        # 缓存幂等性结果
        if request.idempotency_key:
            self._save_idempotency_result(request.idempotency_key, response)

        logger.info(f"✅ 批量删除资产完成: 成功={successful_count}, 失败={failed_count}")

        self._schedule_batch_audit(response, request)

        return response

    async def deactivate_assets_batch(
        self,
        asset_ids: List[str],
        stop_on_first_error: bool = False,
        idempotency_key: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BatchOperationResponse:
        """
        批量停用资产

        Args:
            asset_ids: 资产ID列表
            stop_on_first_error: 遇错是否停止
            idempotency_key: 幂等性键

        Returns:
            批量操作响应
        """
        operation_id = f"asset-deactivate-batch-{uuid.uuid4().hex[:8]}"
        logger.info(f"⏸️ 开始批量停用资产: operation_id={operation_id}, items={len(asset_ids)}")

        # 检查幂等性
        if idempotency_key:
            idempotency_result = self._check_idempotency(idempotency_key, "asset_deactivate")
            if idempotency_result.is_idempotent:
                logger.info(f"✅ 幂等性命中: {idempotency_key}")
                return idempotency_result.cached_result

        results = []
        successful_count = 0
        failed_count = 0
        error_summary = defaultdict(int)

        started_at = datetime.now(timezone.utc)

        for asset_id in asset_ids:
            try:
                # 调用资产停用逻辑
                result = await _deactivate_single_asset(asset_id, self.database)

                item_result = BatchItemResult(
                    id=asset_id, success=True, message="资产停用成功", data=result
                )
                successful_count += 1
                results.append(item_result)

            except Exception as e:
                error_msg = str(e)
                error_type = _classify_error(error_msg)
                error_summary[error_type] += 1
                failed_count += 1

                item_result = BatchItemResult(
                    id=asset_id,
                    success=False,
                    message=f"资产停用失败: {error_msg}",
                    error_code=error_type,
                )
                results.append(item_result)

                if stop_on_first_error:
                    logger.warning(f"⚠️ 遇到错误，停止处理: {error_msg}")
                    break

        # 构建响应
        completed_at = datetime.now(timezone.utc)
        total_items = len(asset_ids)
        success_rate = (successful_count / total_items * 100) if total_items > 0 else 0.0

        status = BatchOperationStatus.COMPLETED
        if failed_count > 0 and successful_count > 0:
            status = BatchOperationStatus.PARTIAL_SUCCESS
        elif failed_count > 0 and successful_count == 0:
            status = BatchOperationStatus.FAILED

        response = BatchOperationResponse(
            operation_id=operation_id,
            operation_type="asset_deactivate",
            status=status,
            summary=BatchOperationSummary(
                total_items=total_items,
                successful_items=successful_count,
                failed_items=failed_count,
                skipped_items=0,
                success_rate=success_rate,
                operation_id=operation_id,
            ),
            results=results,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=dict(error_summary),
        )

        # 缓存幂等性结果
        if idempotency_key:
            self._save_idempotency_result(idempotency_key, response)

        logger.info(f"✅ 批量停用资产完成: 成功={successful_count}, 失败={failed_count}")

        self._schedule_batch_audit(
            response,
            {
                "asset_ids": asset_ids,
                "stop_on_first_error": stop_on_first_error,
                "idempotency_key": idempotency_key,
                "user_id": user_id,
                "username": username,
                "request_ip": request_ip,
                "user_agent": user_agent,
            },
        )

        return response

    async def dispatch_tasks_batch(
        self, request: TaskBatchDispatchRequest
    ) -> BatchOperationResponse:
        """
        批量下发任务

        Args:
            request: 批量任务下发请求

        Returns:
            批量操作响应
        """
        operation_id = f"task-dispatch-batch-{uuid.uuid4().hex[:8]}"
        logger.info(
            f"📤 开始批量下发任务: operation_id={operation_id}, tasks={len(request.task_ids)}, nodes={len(request.target_node_ids)}"
        )

        # 检查幂等性
        if request.idempotency_key:
            idempotency_result = self._check_idempotency(request.idempotency_key, "task_dispatch")
            if idempotency_result.is_idempotent:
                logger.info(f"✅ 幂等性命中: {request.idempotency_key}")
                return idempotency_result.cached_result

        results = []
        successful_count = 0
        failed_count = 0
        error_summary = defaultdict(int)

        started_at = datetime.now(timezone.utc)

        # 为每个任务分配到每个节点
        dispatch_pairs = []
        for task_id in request.task_ids:
            for node_id in request.target_node_ids:
                dispatch_pairs.append((task_id, node_id))

        # 执行批量下发
        for task_id, node_id in dispatch_pairs:
            try:
                # 调用任务下发逻辑
                result = await _dispatch_single_task(
                    task_id, node_id, request.dispatch_options, self.database
                )

                item_result = BatchItemResult(
                    id=f"{task_id}->{node_id}",
                    success=True,
                    message=f"任务{task_id}下发到节点{node_id}成功",
                    data=result,
                )
                successful_count += 1
                results.append(item_result)

            except Exception as e:
                error_msg = str(e)
                error_type = _classify_error(error_msg)
                error_summary[error_type] += 1
                failed_count += 1

                item_result = BatchItemResult(
                    id=f"{task_id}->{node_id}",
                    success=False,
                    message=f"任务下发失败: {error_msg}",
                    error_code=error_type,
                )
                results.append(item_result)

        # 构建响应
        completed_at = datetime.now(timezone.utc)
        total_items = len(dispatch_pairs)
        success_rate = (successful_count / total_items * 100) if total_items > 0 else 0.0

        status = BatchOperationStatus.COMPLETED
        if failed_count > 0 and successful_count > 0:
            status = BatchOperationStatus.PARTIAL_SUCCESS
        elif failed_count > 0 and successful_count == 0:
            status = BatchOperationStatus.FAILED

        response = BatchOperationResponse(
            operation_id=operation_id,
            operation_type="task_dispatch",
            status=status,
            summary=BatchOperationSummary(
                total_items=total_items,
                successful_items=successful_count,
                failed_items=failed_count,
                skipped_items=0,
                success_rate=success_rate,
                operation_id=operation_id,
            ),
            results=results,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=dict(error_summary),
        )

        # 缓存幂等性结果
        if request.idempotency_key:
            self._save_idempotency_result(request.idempotency_key, response)

        logger.info(f"✅ 批量下发任务完成: 成功={successful_count}, 失败={failed_count}")

        self._schedule_batch_audit(response, request)

        return response

    def _check_idempotency(self, idempotency_key: str, operation_type: str) -> IdempotencyResult:
        """检查幂等性"""
        cache_key = f"{operation_type}:{idempotency_key}"

        if cache_key in self._idempotency_cache:
            cached_result = self._idempotency_cache[cache_key]
            return IdempotencyResult(
                is_idempotent=True,
                existing_operation_id=cached_result.operation_id,
                cached_result=cached_result,
                message="操作已存在，返回缓存结果",
            )

        return IdempotencyResult(is_idempotent=False, message="幂等性检查通过，可以执行新操作")

    def _save_idempotency_result(self, idempotency_key: str, result: BatchOperationResponse):
        """保存幂等性结果"""
        operation_type = result.operation_type
        cache_key = f"{operation_type}:{idempotency_key}"
        self._idempotency_cache[cache_key] = result


# ==================== 辅助函数 ====================


async def _create_assets_batch(assets_data: Dict[str, Dict], database) -> Dict[str, bool]:
    """
    批量创建资产（优化版）

    Args:
        assets_data: 资产ID到资产数据的字典
        database: 数据库实例

    Returns:
        资产ID到创建结果的字典
    """
    original_snapshots: Dict[str, Optional[Dict[str, Any]]] = {}
    if database and hasattr(database, "get_device"):
        for asset_id in assets_data.keys():
            try:
                original_snapshots[asset_id] = copy.deepcopy(database.get_device(asset_id))
            except Exception:
                original_snapshots[asset_id] = None

    if database and hasattr(database, "add_devices_batch"):
        try:
            # 使用批量数据库操作
            return database.add_devices_batch(assets_data)
        except Exception as e:
            # 批量操作失败，回退到逐个操作
            logger.warning(f"批量创建操作失败，回退到逐个处理: {str(e)}")
            if original_snapshots and hasattr(database, "lock") and hasattr(database, "devices"):
                with database.lock:
                    for asset_id, original_data in original_snapshots.items():
                        if original_data is None:
                            database.devices.pop(asset_id, None)
                        else:
                            database.devices[asset_id] = copy.deepcopy(original_data)

    # 回退到逐个操作
    results = {}
    for asset_id, asset_data in assets_data.items():
        try:
            if database:
                database.add_device(asset_id, asset_data)
                results[asset_id] = True
            else:
                results[asset_id] = True
        except Exception:
            results[asset_id] = False
    return results


async def _create_single_asset(asset_data: Dict[str, Any], database) -> Dict[str, Any]:
    """创建单个资产"""
    if database:
        # 使用数据库创建资产
        asset_id = asset_data.get("asset_id")
        database.add_device(asset_id, asset_data)
        return database.get_device(asset_id)
    else:
        # 简化实现：直接返回数据
        return asset_data


async def _update_assets_batch(updates: Dict[str, Dict], database) -> Dict[str, bool]:
    """
    批量更新资产（优化版）

    Args:
        updates: 资产ID到更新数据的字典
        database: 数据库实例

    Returns:
        资产ID到更新结果的字典
    """
    if database and hasattr(database, "update_devices_batch"):
        # 使用批量数据库操作
        return database.update_devices_batch(updates)
    else:
        # 回退到逐个操作
        results = {}
        for asset_id, asset_updates in updates.items():
            try:
                if database:
                    success = database.update_device(asset_id, asset_updates)
                    results[asset_id] = success
                else:
                    results[asset_id] = True
            except Exception:
                results[asset_id] = False
        return results


async def _update_assets_batch_with_rollback(updates: Dict[str, Dict], database) -> Dict[str, bool]:
    """
    批量更新资产（带回滚机制）

    Args:
        updates: 资产ID到更新数据的字典
        database: 数据库实例

    Returns:
        资产ID到更新结果的字典
    """
    original_snapshots: Dict[str, Optional[Dict[str, Any]]] = {}
    if database and hasattr(database, "get_device"):
        for asset_id in updates.keys():
            try:
                original_snapshots[asset_id] = copy.deepcopy(database.get_device(asset_id))
            except Exception:
                original_snapshots[asset_id] = None

    if database and hasattr(database, "update_devices_batch"):
        try:
            # 使用批量数据库操作
            return database.update_devices_batch(updates)
        except Exception as e:
            # 批量操作失败，回退到逐个操作（这样可以在失败时回滚）
            logger.warning(f"批量更新操作失败，回退到逐个处理: {str(e)}")
            if original_snapshots and hasattr(database, "lock") and hasattr(database, "devices"):
                with database.lock:
                    for asset_id, original_data in original_snapshots.items():
                        if original_data is None:
                            database.devices.pop(asset_id, None)
                        else:
                            database.devices[asset_id] = copy.deepcopy(original_data)
            results = {}
            for asset_id, asset_updates in updates.items():
                try:
                    if database:
                        success = database.update_device(asset_id, asset_updates)
                        results[asset_id] = success
                    else:
                        # 简化实现：模拟真实数据库行为
                        # 在测试环境中，我们需要模拟不存在的资产返回False
                        # 这里假设所有资产都存在（简化逻辑）
                        # 但为了测试一致性，我们应该正确处理
                        # 检查是否有预先创建的资产（通过检查是否有devices字典）
                        if hasattr(database, "devices") and asset_id not in database.devices:
                            results[asset_id] = False
                        else:
                            results[asset_id] = True
                except Exception:
                    results[asset_id] = False
            return results
    else:
        # 回退到逐个操作
        results = {}
        for asset_id, asset_updates in updates.items():
            try:
                if database:
                    success = database.update_device(asset_id, asset_updates)
                    results[asset_id] = success
                else:
                    results[asset_id] = True
            except Exception:
                results[asset_id] = False
        return results


async def _rollback_asset_updates(
    asset_ids: List[str], original_updates: Dict[str, Any], database
) -> bool:
    """
    回滚资产更新

    Args:
        asset_ids: 需要回滚的资产ID列表
        original_updates: 原始更新数据
        database: 数据库实例

    Returns:
        回滚是否成功
    """
    try:
        if database and hasattr(database, "get_device"):
            # 获取原始数据并恢复
            for asset_id in asset_ids:
                try:
                    # 简单的回滚策略：将更新的字段恢复为原始值的相反操作
                    # 这里可以根据实际需求实现更复杂的回滚逻辑
                    current_data = database.get_device(asset_id)
                    if current_data:
                        # 移除更新的字段
                        for field in original_updates.keys():
                            if field in current_data:
                                del current_data[field]
                        database.update_device(asset_id, {"rolled_back": True})
                except Exception as e:
                    logger.error(f"回滚资产 {asset_id} 失败: {str(e)}")
        return True
    except Exception as e:
        logger.error(f"批量回滚失败: {str(e)}")
        return False


async def _update_single_asset(asset_id: str, updates: Dict[str, Any], database) -> Dict[str, Any]:
    """更新单个资产"""
    if database:
        # 使用数据库更新资产
        success = database.update_device(asset_id, updates)
        if not success:
            raise ValueError(f"资产不存在: {asset_id}")
        return database.get_device(asset_id)
    else:
        # 简化实现：直接返回更新数据
        return {"asset_id": asset_id, **updates}


async def _validate_assets_batch(
    assets: List[Dict[str, Any]], operation_id: str
) -> BatchOperationResponse:
    """验证资产批量创建"""
    results = []
    for i, asset_data in enumerate(assets):
        asset_id = asset_data.get("asset_id", f"unknown-{i}")
        # 简化验证：检查必需字段
        if not asset_data.get("name"):
            results.append(
                BatchItemResult(
                    id=asset_id,
                    success=False,
                    message="缺少必需字段: name",
                    error_code="validation_error",
                )
            )
        else:
            results.append(
                BatchItemResult(id=asset_id, success=True, message="验证通过", data=asset_data)
            )

    successful_count = sum(1 for r in results if r.success)
    failed_count = len(results) - successful_count

    return BatchOperationResponse(
        operation_id=operation_id,
        operation_type="asset_create_validate",
        status=BatchOperationStatus.COMPLETED,
        summary=BatchOperationSummary(
            total_items=len(assets),
            successful_items=successful_count,
            failed_items=failed_count,
            skipped_items=0,
            success_rate=(successful_count / len(assets) * 100) if assets else 0.0,
            operation_id=operation_id,
        ),
        results=results,
        error_summary={},
    )


async def _validate_assets_update_batch(
    asset_ids: List[str], updates: Dict[str, Any], operation_id: str
) -> BatchOperationResponse:
    """验证资产批量更新"""
    results = []
    for asset_id in asset_ids:
        # 简化验证：检查更新字段
        if not updates:
            results.append(
                BatchItemResult(
                    id=asset_id,
                    success=False,
                    message="没有要更新的字段",
                    error_code="validation_error",
                )
            )
        else:
            results.append(
                BatchItemResult(
                    id=asset_id,
                    success=True,
                    message="验证通过",
                    data={"asset_id": asset_id, "updates": updates},
                )
            )

    successful_count = sum(1 for r in results if r.success)
    failed_count = len(results) - successful_count

    return BatchOperationResponse(
        operation_id=operation_id,
        operation_type="asset_update_validate",
        status=BatchOperationStatus.COMPLETED,
        summary=BatchOperationSummary(
            total_items=len(asset_ids),
            successful_items=successful_count,
            failed_items=failed_count,
            skipped_items=0,
            success_rate=((successful_count / len(asset_ids) * 100) if asset_ids else 0.0),
            operation_id=operation_id,
        ),
        results=results,
        error_summary={},
    )


async def _create_tasks_parallel(
    tasks: List[Dict[str, Any]],
    max_parallel: int,
    stop_on_first_error: bool,
    operation_id: str,
    database,
) -> List[BatchItemResult]:
    """并行创建任务"""
    semaphore = asyncio.Semaphore(max_parallel)
    results = []

    async def create_with_semaphore(task_data, index):
        async with semaphore:
            try:
                task_id = task_data.get("task_id", f"task-{index}")
                # 调用任务创建逻辑
                if database:
                    database.add_job(task_id, task_data)
                    result = database.get_job(task_id)
                else:
                    result = task_data

                return BatchItemResult(id=task_id, success=True, message="任务创建成功", data=result)
            except Exception as e:
                return BatchItemResult(
                    id=task_data.get("task_id", f"task-{index}"),
                    success=False,
                    message=f"任务创建失败: {str(e)}",
                    error_code=_classify_error(str(e)),
                )

    # 创建所有任务
    tasks_to_create = [create_with_semaphore(task_data, i) for i, task_data in enumerate(tasks)]

    # 并行执行
    completed_results = await asyncio.gather(*tasks_to_create, return_exceptions=True)

    # 处理结果
    for result in completed_results:
        if isinstance(result, Exception):
            results.append(
                BatchItemResult(
                    id="unknown",
                    success=False,
                    message=f"任务执行异常: {str(result)}",
                    error_code="execution_error",
                )
            )
        else:
            results.append(result)

        # 如果需要遇错停止
        if stop_on_first_error and not results[-1].success:
            break

    return results


async def _create_tasks_sequential(
    tasks: List[Dict[str, Any]], stop_on_first_error: bool, operation_id: str, database
) -> List[BatchItemResult]:
    """顺序创建任务"""
    results = []

    for i, task_data in enumerate(tasks):
        try:
            task_id = task_data.get("task_id", f"task-{i}")
            # 调用任务创建逻辑
            if database:
                database.add_job(task_id, task_data)
                result = database.get_job(task_id)
            else:
                result = task_data

            results.append(BatchItemResult(id=task_id, success=True, message="任务创建成功", data=result))

        except Exception as e:
            results.append(
                BatchItemResult(
                    id=task_data.get("task_id", f"task-{i}"),
                    success=False,
                    message=f"任务创建失败: {str(e)}",
                    error_code=_classify_error(str(e)),
                )
            )

            if stop_on_first_error:
                break

    return results


async def _delete_single_asset(asset_id: str, force: bool, database) -> Dict[str, Any]:
    """删除单个资产"""
    if database:
        # 使用数据库删除资产
        device = database.get_device(asset_id)
        if not device:
            raise ValueError(f"资产不存在: {asset_id}")

        # 检查是否有关联任务
        jobs = database.list_jobs()
        related_jobs = [job for job in jobs if job.get("device_id") == asset_id]

        if related_jobs and not force:
            raise ValueError(f"资产有关联任务，无法删除: {len(related_jobs)}个任务")

        # 删除资产
        success = database.update_device(asset_id, {"status": "deleted"})
        if not success:
            raise ValueError(f"资产删除失败: {asset_id}")

        return {"asset_id": asset_id, "status": "deleted", "forced": force}
    else:
        # 简化实现：直接返回删除数据
        return {"asset_id": asset_id, "status": "deleted", "forced": force}


async def _deactivate_single_asset(asset_id: str, database) -> Dict[str, Any]:
    """停用单个资产"""
    if database:
        # 使用数据库停用资产
        device = database.get_device(asset_id)
        if not device:
            raise ValueError(f"资产不存在: {asset_id}")

        # 停用资产
        success = database.update_device(asset_id, {"status": "inactive"})
        if not success:
            raise ValueError(f"资产停用失败: {asset_id}")

        return database.get_device(asset_id)
    else:
        # 简化实现：直接返回停用数据
        return {"asset_id": asset_id, "status": "inactive"}


async def _dispatch_single_task(
    task_id: str, node_id: str, options: Dict[str, Any], database
) -> Dict[str, Any]:
    """下发单个任务到节点"""
    if database:
        # 检查任务和节点
        job = database.get_job(task_id)
        if not job:
            raise ValueError(f"任务不存在: {task_id}")

        node = database.get_node(node_id)
        if not node:
            raise ValueError(f"节点不存在: {node_id}")

        # 更新任务状态为已下发
        database.update_job(
            task_id,
            {
                "node_id": node_id,
                "status": "dispatched",
                "dispatched_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return database.get_job(task_id)
    else:
        # 简化实现：直接返回下發数据
        return {
            "task_id": task_id,
            "node_id": node_id,
            "status": "dispatched",
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
        }


def _validate_asset_data(asset_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    校验资产数据

    Args:
        asset_data: 资产数据

    Returns:
        校验结果: {"valid": bool, "error": str}
    """
    # 检查必需字段
    required_fields = ["asset_id", "name", "asset_type"]
    missing_fields = [
        field for field in required_fields if field not in asset_data or not asset_data[field]
    ]

    if missing_fields:
        return {"valid": False, "error": f"缺少必需字段: {', '.join(missing_fields)}"}

    # 检查字段类型和格式
    asset_id = asset_data.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id.strip():
        return {"valid": False, "error": "asset_id 必须是非空字符串"}

    asset_type = asset_data.get("asset_type")
    valid_asset_types = ["linux_host", "network_device", "iot_device", "edge_node"]
    if asset_type not in valid_asset_types:
        return {
            "valid": False,
            "error": f"asset_type 必须是以下之一: {', '.join(valid_asset_types)}",
        }

    # 检查名称
    name = asset_data.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"valid": False, "error": "name 必须是非空字符串"}

    return {"valid": True, "error": None}


def _classify_error(error_message: str) -> str:
    """分类错误类型"""
    error_message_lower = error_message.lower()

    if "validation" in error_message_lower or "invalid" in error_message_lower:
        return "validation_error"
    elif "duplicate" in error_message_lower or "exists" in error_message_lower:
        return "duplicate_error"
    elif "not found" in error_message_lower or "does not exist" in error_message_lower:
        return "not_found_error"
    elif "timeout" in error_message_lower:
        return "timeout"
    elif "permission" in error_message_lower or "unauthorized" in error_message_lower:
        return "permission_error"
    elif "connection" in error_message_lower:
        return "connection_error"
    else:
        return "unknown_error"


# 全局服务实例
_batch_operation_service = None


def get_batch_operation_service(database=None) -> BatchOperationService:
    """获取批量操作服务实例"""
    global _batch_operation_service
    if _batch_operation_service is None:
        _batch_operation_service = BatchOperationService(database)
    return _batch_operation_service
