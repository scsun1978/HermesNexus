#!/usr/bin/env python3
"""
Edge节点修复脚本
修复Edge节点的cloud_url配置，从localhost:8080改为172.16.100.101:8082
"""

import sys
import os
import re
from datetime import datetime

def find_edge_node_files():
    """查找Edge节点文件"""
    possible_paths = [
        "/home/scsun/hermesnexus-code/edge/enhanced_edge_node_v12.py",
        "/home/scsun/hermesnexus/edge/enhanced_edge_node_v12.py",
        "/home/scsun/hermesnexus/final-edge-node.py",
        "/home/scsun/hermesnexus-code/final-edge-node.py",
    ]

    found_files = []
    for path in possible_paths:
        if os.path.exists(path):
            found_files.append(path)

    return found_files

def fix_edge_node_config(file_path):
    """修复Edge节点配置"""
    print(f"🔧 正在修复: {file_path}")

    # 读取文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 无法读取文件: {e}")
        return False

    original_content = content

    # 修复各种可能的配置错误
    fixes_applied = []

    # 1. 修复 localhost:8080 -> 172.16.100.101:8082
    if 'localhost:8080' in content:
        content = content.replace('localhost:8080', '172.16.100.101:8082')
        fixes_applied.append('localhost:8080 -> 172.16.100.101:8082')

    # 2. 修复 cloud_url = "http://...8080" -> 8082
    content = re.sub(r'cloud_url.*8080', 'cloud_url = "http://172.16.100.101:8082"', content)
    if 'cloud_url' in content and '8082' in content:
        if not any('cloud_url' in fix for fix in fixes_applied):
            fixes_applied.append('cloud_url -> http://172.16.100.101:8082')

    # 3. 修复端口8080 -> 8082 (在上下文中)
    content = re.sub(r':8080"', ':8082"', content)
    content = re.sub(r':8080\'', ':8082\'', content)

    if content != original_content:
        # 备份原文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        os.system(f"cp {file_path} {backup_path}")
        print(f"✅ 文件已备份: {backup_path}")

        # 写入修复后的内容
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("✅ Edge节点配置已修复")
            for fix in fixes_applied:
                print(f"   - {fix}")
            return True
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False
    else:
        print("✅ Edge节点配置正确，无需修复")
        return True

def stop_old_edge_processes():
    """停止旧的Edge节点进程"""
    print("🛑 停止旧的Edge节点进程...")

    # 查找并停止所有相关进程
    os.system("pkill -f final-edge-node.py 2>/dev/null || true")
    os.system("sleep 2")
    os.system("pkill -9 -f final-edge-node.py 2>/dev/null || true")
    os.system("pkill -9 -f enhanced_edge_node 2>/dev/null || true")

    print("✅ 旧Edge节点进程已停止")

def start_edge_node(file_path):
    """启动Edge节点"""
    print(f"🚀 启动Edge节点: {file_path}")

    log_dir = "/home/scsun/hermesnexus-logs"
    pid_file = "/tmp/edge-node-fixed.pid"

    # 确保日志目录存在
    os.system(f"mkdir -p {log_dir}")

    # 启动Edge节点
    log_file = f"{log_dir}/edge-node-fixed.log"
    cmd = f"nohup python3 {file_path} > {log_file} 2>&1 & echo $! > {pid_file}"

    print(f"📝 日志文件: {log_file}")
    print(f"📝 PID文件: {pid_file}")

    result = os.system(cmd)

    if result == 0:
        # 等待进程启动
        os.system("sleep 3")

        # 检查进程是否运行
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = f.read().strip()
            print(f"✅ Edge节点已启动 (PID: {pid})")
            return True
        else:
            print("⚠️ Edge节点启动状态未知，请检查日志")
            return True
    else:
        print("❌ Edge节点启动失败")
        return False

def main():
    print("=== HermesNexus Edge节点修复脚本 ===")
    print("修复Edge节点配置，使其正确连接到Cloud API")
    print("")

    # 1. 查找Edge节点文件
    print("🔍 步骤1: 查找Edge节点文件...")
    edge_files = find_edge_node_files()

    if not edge_files:
        print("❌ 未找到任何Edge节点文件")
        print("📋 可能的路径:")
        for path in [
            "/home/scsun/hermesnexus-code/edge/enhanced_edge_node_v12.py",
            "/home/scsun/hermesnexus/final-edge-node.py"
        ]:
            print(f"   - {path}")
        return 1

    print(f"✅ 找到 {len(edge_files)} 个Edge节点文件:")
    for file in edge_files:
        print(f"   - {file}")

    # 选择优先级最高的文件（enhanced版本优先）
    edge_file = edge_files[0]
    print(f"🎯 选择修复: {edge_file}")

    # 2. 修复配置
    print("")
    print("🔧 步骤2: 修复Edge节点配置...")
    if not fix_edge_node_config(edge_file):
        print("❌ 配置修复失败")
        return 1

    # 3. 停止旧进程
    print("")
    stop_old_edge_processes()

    # 等待进程完全停止
    import time
    time.sleep(2)

    # 4. 启动新Edge节点
    print("")
    if not start_edge_node(edge_file):
        print("❌ Edge节点启动失败")
        return 1

    # 5. 提供验证指导
    print("")
    print("=== Edge节点修复完成 ===")
    print("")
    print("📋 验证命令:")
    print("   # 检查Edge节点健康状态")
    print("   curl http://localhost:8081/health")
    print("")
    print("   # 检查Edge节点日志")
    print("   tail -f /home/scsun/hermesnexus-logs/edge-node-fixed.log")
    print("")
    print("   # 检查进程状态")
    print("   ps aux | grep edge.*node")
    print("")
    print("🎯 预期结果:")
    print("   - Edge节点应返回健康状态")
    print("   - 日志中不应再有localhost:8080连接错误")
    print("   - Edge节点应连接到172.16.100.101:8082")
    print("")

    return 0

if __name__ == '__main__':
    sys.exit(main())