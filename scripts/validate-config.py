#!/usr/bin/env python3
"""
HermesNexus Configuration Validation Script
配置验证脚本
"""

import os
import sys
from pathlib import Path
from typing import List


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> bool:
        """执行完整验证"""
        print("HermesNexus Configuration Validation")
        print("=" * 50)

        self.validate_environment()
        self.validate_directories()
        self.validate_database()
        self.validate_network()

        self.report_results()
        return len(self.errors) == 0

    def validate_environment(self):
        """验证环境变量"""
        print("\n📋 Validating Environment Variables...")

        # 检查必需的环境变量
        required_vars = {
            "HERMES_ENV": "运行环境",
            "CLOUD_API_PORT": "API端口",
            "LOG_LEVEL": "日志级别",
        }

        for var, desc in required_vars.items():
            if not os.getenv(var):
                self.errors.append(f"缺少必需的环境变量: {var} ({desc})")
            else:
                print(f"  ✓ {var}: {os.getenv(var)}")

        # 检查 Edge Node 特定变量
        if os.getenv("HERMES_ENV") == "production":
            edge_vars = {
                "NODE_ID": "节点ID",
                "NODE_NAME": "节点名称",
                "CLOUD_API_URL": "Cloud API地址",
            }

            for var, desc in edge_vars.items():
                if not os.getenv(var):
                    self.errors.append(f"生产环境缺少必需变量: {var} ({desc})")

        # 检查可选但推荐的变量
        recommended_vars = {
            "SECRET_KEY": "API密钥",
            "DATA_DIR": "数据目录",
            "LOG_DIR": "日志目录",
        }

        for var, desc in recommended_vars.items():
            if not os.getenv(var):
                self.warnings.append(f"缺少推荐的环境变量: {var} ({desc})")

    def validate_directories(self):
        """验证目录结构"""
        print("\n📁 Validating Directories...")

        required_dirs = [
            os.getenv("DATA_DIR", "./data"),
            os.getenv("LOG_DIR", "./logs"),
            os.getenv("ASSETS_DIR", "./data/assets"),
            os.getenv("TASKS_DIR", "./data/tasks"),
            os.getenv("SCRIPTS_DIR", "./data/scripts"),
        ]

        for dir_path in required_dirs:
            path = Path(dir_path)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"  ✓ 创建目录: {dir_path}")
                except Exception as e:
                    self.errors.append(f"无法创建目录 {dir_path}: {e}")
            else:
                if not os.access(dir_path, os.W_OK):
                    self.errors.append(f"目录不可写: {dir_path}")
                else:
                    print(f"  ✓ {dir_path}: 可写")

    def validate_database(self):
        """验证数据库配置"""
        print("\n🗄️  Validating Database Configuration...")

        db_type = os.getenv("DATABASE_TYPE", "sqlite")
        db_url = os.getenv("DATABASE_URL")

        if not db_url:
            self.errors.append("缺少数据库连接配置: DATABASE_URL")
            return

        print(f"  数据库类型: {db_type}")

        if db_type == "sqlite":
            # 检查 SQLite 数据库文件目录
            db_path = db_url.replace("sqlite:///", "")
            db_file = Path(db_path)

            if not db_file.parent.exists():
                try:
                    db_file.parent.mkdir(parents=True, exist_ok=True)
                    print(f"  ✓ 创建数据库目录: {db_file.parent}")
                except Exception as e:
                    self.errors.append(f"无法创建数据库目录: {e}")
            else:
                print(f"  ✓ 数据库目录: {db_file.parent}")

                if db_file.exists():
                    size = db_file.stat().st_size / 1024  # KB
                    print(f"  ✓ 数据库文件: {db_file.name} ({size:.2f} KB)")
                else:
                    self.warnings.append(f"数据库文件不存在，将自动创建: {db_file}")

        elif db_type == "postgresql":
            # 简单验证 PostgreSQL 连接字符串格式
            if not db_url.startswith("postgresql://"):
                self.errors.append(f"无效的 PostgreSQL 连接字符串格式: {db_url}")
            else:
                print(
                    f"  ✓ PostgreSQL 连接: {db_url.split('@')[-1] if '@' in db_url else 'unknown'}"
                )

    def validate_network(self):
        """验证网络配置"""
        print("\n🌐 Validating Network Configuration...")

        port = os.getenv("CLOUD_API_PORT", "8080")
        host = os.getenv("CLOUD_API_HOST", "127.0.0.1")

        print(f"  监听地址: {host}:{port}")

        # 检查端口是否被占用
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, int(port)))
            sock.close()

            if result == 0:
                self.warnings.append(f"端口 {port} 已被占用，可能无法启动服务")
            else:
                print(f"  ✓ 端口 {port}: 可用")
        except Exception as e:
            self.warnings.append(f"无法检查端口占用情况: {e}")

        # 检查 Cloud API 连接（如果是 Edge Node）
        if os.getenv("NODE_ID") and os.getenv("CLOUD_API_URL"):
            import urllib.parse

            cloud_url = os.getenv("CLOUD_API_URL")
            parsed = urllib.parse.urlparse(cloud_url)

            print(f"  Cloud API: {parsed.netloc or cloud_url}")

            try:
                import urllib.request

                health_url = f"{cloud_url.rstrip('/')}/health"
                req = urllib.request.Request(health_url)
                req.add_header("User-Agent", "HermesNexus-ConfigValidator/1.0")

                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        print("  ✓ Cloud API 可达")
                    else:
                        self.warnings.append(f"Cloud API 返回状态码: {response.status}")
            except Exception as e:
                self.warnings.append(f"无法连接到 Cloud API: {e}")

    def report_results(self):
        """报告验证结果"""
        print("\n" + "=" * 50)
        print("Validation Results")
        print("=" * 50)

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
            print("\n❌ Configuration validation: FAILED")
            sys.exit(1)
        else:
            print("\n✅ Configuration validation: PASSED")

            if self.warnings:
                print(f"\n⚠️  Passed with {len(self.warnings)} warnings")
            else:
                print("\n🎉 All checks passed!")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="HermesNexus Configuration Validator")
    parser.add_argument("--env", type=str, help="Environment file to load (.env.<env>)")
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )

    args = parser.parse_args()

    # 加载环境文件
    if args.env:
        env_file = f".env.{args.env}"
        if os.path.exists(env_file):
            print(f"Loading environment from: {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
        else:
            print(f"Warning: Environment file not found: {env_file}")

    # 执行验证
    validator = ConfigValidator()
    success = validator.validate()

    # 严格模式：将警告视为错误
    if args.strict and validator.warnings:
        print("\n❌ Strict mode: Warnings treated as errors")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
