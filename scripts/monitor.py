#!/usr/bin/env python3
"""
HermesNexus 系统监控脚本
实时监控系统健康状态、性能指标和资源使用情况
"""

import requests
import psutil
import time
import json
import logging
from datetime import datetime
from pathlib import Path

# 配置
API_BASE_URL = "http://localhost:8080"
CHECK_INTERVAL = 30  # 检查间隔(秒)
LOG_FILE = "./logs/monitor.log"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SystemMonitor:
    """系统监控器"""

    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.check_interval = CHECK_INTERVAL

    def check_api_health(self):
        """检查API健康状态"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def get_system_stats(self):
        """获取系统统计信息"""
        try:
            response = requests.get(f"{self.api_base_url}/api/v1/stats", timeout=5)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def get_nodes_status(self):
        """获取节点状态"""
        try:
            response = requests.get(f"{self.api_base_url}/api/v1/nodes", timeout=5)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def get_system_resources(self):
        """获取系统资源使用情况"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                }
            }
        except Exception as e:
            logger.error(f"获取系统资源失败: {e}")
            return None

    def check_database_status(self):
        """检查数据库状态"""
        db_path = Path(os.getenv("SQLITE_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "hermesnexus.db")))
        try:
            if db_path.exists():
                size = db_path.stat().st_size
                return True, {'exists': True, 'size': size, 'path': str(db_path)}
            else:
                return False, {'exists': False, 'path': str(db_path)}
        except Exception as e:
            return False, str(e)

    def check_log_files(self):
        """检查日志文件状态"""
        log_dir = Path("./logs")
        try:
            if not log_dir.exists():
                return {'exists': False, 'files': []}

            log_files = []
            for log_file in log_dir.glob("*.log"):
                stat = log_file.stat()
                log_files.append({
                    'name': log_file.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

            return {'exists': True, 'files': log_files, 'count': len(log_files)}
        except Exception as e:
            logger.error(f"检查日志文件失败: {e}")
            return {'exists': False, 'error': str(e)}

    def format_bytes(self, bytes_value):
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"

    def display_status(self):
        """显示系统状态"""
        print("\n" + "="*80)
        print(f"🔍 HermesNexus 系统监控报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # API健康状态
        api_healthy, api_result = self.check_api_health()
        print(f"\n🌐 API健康状态: {'✅ 健康' if api_healthy else '❌ 异常'}")
        if api_healthy:
            print(f"   状态: {api_result.get('status', 'unknown')}")
            print(f"   时间戳: {api_result.get('timestamp', 'unknown')}")
        else:
            print(f"   错误: {api_result}")

        # 系统统计
        stats_healthy, stats_result = self.get_system_stats()
        print(f"\n📊 系统统计: {'✅ 正常' if stats_healthy else '❌ 异常'}")
        if stats_healthy:
            print(f"   节点总数: {stats_result.get('total_nodes', 0)}")
            print(f"   在线节点: {stats_result.get('online_nodes', 0)}")
            print(f"   设备总数: {stats_result.get('total_devices', 0)}")
            print(f"   任务总数: {stats_result.get('total_jobs', 0)}")
            print(f"   事件总数: {stats_result.get('total_events', 0)}")
        else:
            print(f"   错误: {stats_result}")

        # 节点状态
        nodes_healthy, nodes_result = self.get_nodes_status()
        print(f"\n🖥️  节点状态: {'✅ 正常' if nodes_healthy else '❌ 异常'}")
        if nodes_healthy:
            for node in nodes_result.get('nodes', []):
                status_icon = "🟢" if node.get('status') == 'online' else "🔴"
                print(f"   {status_icon} {node.get('node_id')}: {node.get('name')}")
                print(f"      CPU: {node.get('cpu_usage', 0):.1f}%, "
                      f"内存: {node.get('memory_usage', 0):.1f}%, "
                      f"任务: {node.get('active_tasks', 0)}")
        else:
            print(f"   错误: {nodes_result}")

        # 系统资源
        resources = self.get_system_resources()
        if resources:
            print(f"\n💻 系统资源:")
            print(f"   CPU使用: {resources['cpu_percent']:.1f}%")
            print(f"   内存使用: {resources['memory']['percent']:.1f}% "
                  f"({self.format_bytes(resources['memory']['used'])} / "
                  f"{self.format_bytes(resources['memory']['total'])})")
            print(f"   磁盘使用: {resources['disk']['percent']:.1f}% "
                  f"({self.format_bytes(resources['disk']['used'])} / "
                  f"{self.format_bytes(resources['disk']['total'])})")

        # 数据库状态
        db_healthy, db_result = self.check_database_status()
        print(f"\n🗄️  数据库状态: {'✅ 正常' if db_healthy else '❌ 异常'}")
        if db_healthy:
            print(f"   文件路径: {db_result['path']}")
            print(f"   文件大小: {self.format_bytes(db_result['size'])}")
        else:
            print(f"   状态: {db_result}")

        # 日志文件状态
        logs_result = self.check_log_files()
        print(f"\n📝 日志文件:")
        if logs_result.get('exists'):
            print(f"   日志目录: ./logs")
            print(f"   文件数量: {logs_result['count']}")
            total_size = sum(f['size'] for f in logs_result['files'])
            print(f"   总大小: {self.format_bytes(total_size)}")
        else:
            print(f"   日志目录不存在")

        # 系统健康评估
        print(f"\n🏥 系统健康评估:")
        health_score = 0
        if api_healthy:
            health_score += 25
            print("   ✅ API服务 (25%)")
        if stats_healthy:
            health_score += 25
            print("   ✅ 系统统计 (25%)")
        if resources and resources['memory']['percent'] < 80:
            health_score += 25
            print("   ✅ 资源使用 (25%)")
        if db_healthy:
            health_score += 25
            print("   ✅ 数据库状态 (25%)")

        print(f"\n   总体评分: {health_score}/100")

        if health_score >= 90:
            print("   状态: 🟢 优秀")
        elif health_score >= 70:
            print("   状态: 🟡 良好")
        else:
            print("   状态: 🔴 需要关注")

        print("="*80 + "\n")

        return health_score >= 70

    def run_once(self):
        """运行一次监控检查"""
        return self.display_status()

    def run_continuous(self):
        """持续监控系统状态"""
        logger.info("🚀 启动持续监控模式...")
        logger.info(f"检查间隔: {self.check_interval}秒")

        try:
            while True:
                try:
                    self.run_once()
                    logger.info(f"✅ 监控检查完成，等待{self.check_interval}秒...")
                    time.sleep(self.check_interval)
                except KeyboardInterrupt:
                    logger.info("👋 收到停止信号，退出监控")
                    break
                except Exception as e:
                    logger.error(f"❌ 监控检查失败: {e}")
                    time.sleep(self.check_interval)
        except Exception as e:
            logger.error(f"❌ 监控程序异常: {e}")

def main():
    """主函数"""
    import sys

    monitor = SystemMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "once":
            # 单次检查
            healthy = monitor.run_once()
            sys.exit(0 if healthy else 1)
        elif command == "continuous":
            # 持续监控
            monitor.run_continuous()
        else:
            print("用法: python monitor.py [once|continuous]")
            print("  once       - 单次健康检查")
            print("  continuous - 持续监控模式")
            sys.exit(1)
    else:
        # 默认单次检查
        healthy = monitor.run_once()
        sys.exit(0 if healthy else 1)

if __name__ == "__main__":
    main()