"""
HermesNexus Phase 2 - Asset Model
资产管理数据模型
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator


class AssetType(str, Enum):
    """资产类型"""

    EDGE_NODE = "edge_node"  # 边缘节点
    LINUX_HOST = "linux_host"  # Linux 主机
    NETWORK_DEVICE = "network_device"  # 网络设备
    IOT_DEVICE = "iot_device"  # IoT 设备


class AssetStatus(str, Enum):
    """资产状态"""

    REGISTERED = "registered"  # 已注册，未关联运行节点
    ACTIVE = "active"  # 活跃，有运行节点在线
    ONLINE = "active"  # 兼容旧测试/旧API
    INACTIVE = "inactive"  # 非活跃，运行节点离线
    OFFLINE = "inactive"  # 兼容旧测试/旧API
    MAINTENANCE = "inactive"  # 兼容旧测试/旧API（映射为非活跃）
    DECOMMISSIONED = "decommissioned"  # 已退役

    def can_transition_to(self, new_status: "AssetStatus") -> bool:
        valid_transitions = {
            AssetStatus.REGISTERED: [
                AssetStatus.ACTIVE,
                AssetStatus.INACTIVE,
                AssetStatus.DECOMMISSIONED,
            ],
            AssetStatus.ACTIVE: [AssetStatus.INACTIVE, AssetStatus.DECOMMISSIONED],
            AssetStatus.INACTIVE: [AssetStatus.ACTIVE, AssetStatus.DECOMMISSIONED],
            AssetStatus.DECOMMISSIONED: [],
        }
        return new_status in valid_transitions.get(self, [])


class AssetMetadata(BaseModel):
    """资产元数据"""

    # 通用属性
    manufacturer: Optional[str] = Field(None, description="厂商")
    model: Optional[str] = Field(None, description="型号")
    serial_number: Optional[str] = Field(None, description="序列号")

    # 网络信息
    ip_address: Optional[str] = Field(None, description="IP地址")
    hostname: Optional[str] = Field(None, description="主机名")
    mac_address: Optional[str] = Field(None, description="MAC地址")

    # SSH 配置（适用于 Linux 主机和边缘节点）
    ssh_port: Optional[int] = Field(22, description="SSH端口")
    ssh_username: Optional[str] = Field(None, description="SSH用户名")
    ssh_key_path: Optional[str] = Field(None, description="SSH密钥路径")

    # 系统信息
    os_type: Optional[str] = Field(None, description="操作系统类型")
    os_version: Optional[str] = Field(None, description="操作系统版本")
    cpu_cores: Optional[int] = Field(None, description="CPU核心数")
    memory_gb: Optional[float] = Field(None, description="内存大小(GB)")
    disk_gb: Optional[float] = Field(None, description="磁盘大小(GB)")

    # 位置信息
    location: Optional[str] = Field(None, description="物理位置")
    rack: Optional[str] = Field(None, description="机架")
    datacenter: Optional[str] = Field(None, description="数据中心")

    # 标签和分组
    tags: List[str] = Field(default_factory=list, description="标签列表")
    groups: List[str] = Field(default_factory=list, description="分组列表")

    # 自定义属性
    custom_properties: Dict[str, Any] = Field(default_factory=dict, description="自定义属性")

    class Config:
        json_schema_extra = {
            "example": {
                "manufacturer": "Dell",
                "model": "PowerEdge R740",
                "serial_number": "CN012345678",
                "ip_address": "192.168.1.100",
                "hostname": "server-001",
                "ssh_port": 22,
                "ssh_username": "root",
                "os_type": "Linux",
                "os_version": "Ubuntu 22.04",
                "cpu_cores": 16,
                "memory_gb": 64.0,
                "disk_gb": 1000.0,
                "location": "Beijing, Room 301",
                "rack": "A01",
                "datacenter": "BJ-DC1",
                "tags": ["production", "web"],
                "groups": ["web-servers"],
                "custom_properties": {
                    "support_contract": "Premium",
                    "maintenance_window": "Sunday 2-4 AM",
                },
            }
        }


class Asset(BaseModel):
    """资产模型"""

    asset_id: str = Field(..., description="资产唯一标识")
    name: str = Field(..., description="资产名称", min_length=1, max_length=255)
    asset_type: AssetType = Field(..., description="资产类型")
    status: AssetStatus = Field(default=AssetStatus.REGISTERED, description="资产状态")
    metadata: AssetMetadata = Field(default_factory=AssetMetadata, description="资产元数据")

    # 关联节点（如果存在）
    associated_node_id: Optional[str] = Field(None, description="关联的运行节点ID")

    # 创建信息
    created_by: Optional[str] = Field(None, description="创建者")

    # 时间戳
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="更新时间"
    )
    last_heartbeat: Optional[datetime] = Field(None, description="最后心跳时间")

    # 描述信息
    description: Optional[str] = Field(None, description="资产描述", max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "asset_id": "asset-001",
                "name": "生产Web服务器-001",
                "asset_type": "linux_host",
                "status": "active",
                "metadata": {
                    "manufacturer": "Dell",
                    "model": "PowerEdge R740",
                    "ip_address": "192.168.1.100",
                    "hostname": "web-001.prod.local",
                },
                "associated_node_id": "node-001",
                "created_at": "2026-04-12T10:00:00Z",
                "updated_at": "2026-04-12T10:00:00Z",
                "last_heartbeat": "2026-04-12T15:30:00Z",
                "description": "主生产Web服务器",
            }
        }

    @validator("asset_id")
    def validate_asset_id(cls, v):
        """验证资产ID格式"""
        if not v or len(v.strip()) == 0:
            raise ValueError("asset_id cannot be empty")
        return v.strip()

    @root_validator(pre=True)
    def _compat_legacy_meta_data(cls, values):
        """兼容旧字段名 meta_data，并把常见的扁平字典转换为 AssetMetadata"""
        if isinstance(values, dict):
            if "metadata" not in values and "meta_data" in values:
                values["metadata"] = values.pop("meta_data")
            metadata = values.get("metadata")
            if isinstance(metadata, dict):
                legacy = dict(metadata)
                normalized = {}
                if "ip" in legacy and "ip_address" not in legacy:
                    normalized["ip_address"] = legacy.pop("ip")
                for key in list(legacy.keys()):
                    if key in AssetMetadata.__fields__:
                        normalized[key] = legacy.pop(key)
                if legacy:
                    normalized["custom_properties"] = legacy
                values["metadata"] = AssetMetadata(**normalized)
        return values

    @validator("name")
    def validate_name(cls, v):
        """验证资产名称"""
        if not v or len(v.strip()) == 0:
            raise ValueError("name cannot be empty")
        return v.strip()


class AssetCreateRequest(BaseModel):
    """资产创建请求"""

    asset_id: Optional[str] = Field(None, description="资产ID（不指定则自动生成）")
    name: str = Field(..., description="资产名称", min_length=1, max_length=255)
    asset_type: AssetType = Field(..., description="资产类型")
    description: Optional[str] = Field(None, description="资产描述", max_length=1000)
    metadata: Optional[AssetMetadata] = Field(
        default_factory=AssetMetadata, description="资产元数据"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "生产Web服务器-001",
                "asset_type": "linux_host",
                "description": "主生产Web服务器",
                "metadata": {
                    "manufacturer": "Dell",
                    "model": "PowerEdge R740",
                    "ip_address": "192.168.1.100",
                    "hostname": "web-001.prod.local",
                },
            }
        }


class AssetUpdateRequest(BaseModel):
    """资产更新请求"""

    name: Optional[str] = Field(None, description="资产名称", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="资产描述", max_length=1000)
    status: Optional[AssetStatus] = Field(None, description="资产状态")
    metadata: Optional[AssetMetadata] = Field(None, description="资产元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "生产Web服务器-001（已更新）",
                "status": "active",
                "metadata": {
                    "ip_address": "192.168.1.101",
                    "tags": ["production", "web", "updated"],
                },
            }
        }


class AssetListResponse(BaseModel):
    """资产列表响应"""

    total: int = Field(..., description="总数量")
    assets: List[Asset] = Field(..., description="资产列表")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "assets": [],
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
            }
        }


class AssetQueryParams(BaseModel):
    """资产查询参数"""

    asset_type: Optional[AssetType] = Field(None, description="按资产类型过滤")
    status: Optional[AssetStatus] = Field(None, description="按状态过滤")
    search: Optional[str] = Field(None, description="搜索关键词（名称、描述、IP地址）")
    tags: Optional[List[str]] = Field(None, description="按标签过滤")
    groups: Optional[List[str]] = Field(None, description="按分组过滤")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页大小")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")

    class Config:
        json_schema_extra = {
            "example": {
                "asset_type": "linux_host",
                "status": "active",
                "search": "web",
                "tags": ["production"],
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc",
            }
        }


# 资产状态统计
class AssetStats(BaseModel):
    """资产统计信息"""

    total_assets: int = Field(..., description="总资产数")
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    by_status: Dict[str, int] = Field(default_factory=dict, description="按状态统计")
    active_nodes: int = Field(..., description="活跃节点数")
    inactive_nodes: int = Field(..., description="非活跃节点数")

    class Config:
        json_schema_extra = {
            "example": {
                "total_assets": 150,
                "by_type": {
                    "edge_node": 10,
                    "linux_host": 120,
                    "network_device": 15,
                    "iot_device": 5,
                },
                "by_status": {
                    "registered": 5,
                    "active": 130,
                    "inactive": 10,
                    "decommissioned": 5,
                },
                "active_nodes": 130,
                "inactive_nodes": 10,
            }
        }
