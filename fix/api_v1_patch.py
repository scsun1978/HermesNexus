#!/usr/bin/env python3
"""
Cloud API v1.2.0 - API v1兼容层补丁
直接在生产服务器上运行此脚本来添加API v1兼容端点
"""

import re
import sys
import os
from datetime import datetime

def backup_file(file_path):
    """备份文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup.{timestamp}"
    os.system(f"cp {file_path} {backup_path}")
    print(f"✅ 文件已备份: {backup_path}")
    return backup_path

def add_api_v1_endpoints(file_path):
    """在Cloud API中添加API v1兼容端点"""

    print(f"🔧 正在修复: {file_path}")

    # 读取文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 无法读取文件: {e}")
        return False

    # 检查是否已经包含API v1端点
    if 'api/v1/tasks' in content:
        print("✅ 代码已包含API v1兼容端点，无需添加")
        return True

    # API v1兼容端点代码
    api_v1_code = '''
                # API v1兼容层 - 支持Edge节点的旧API契约
                elif path == '/api/v1/tasks':
                    # API v1任务列表端点
                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100')
                    jobs = cursor.fetchall()

                    job_list = []
                    for job in jobs:
                        try:
                            result_data = json.loads(job[7]) if job[7] else None
                        except:
                            result_data = None

                        job_list.append({
                            "job_id": job[1],
                            "name": job[2],
                            "job_type": job[3],
                            "status": job[4],
                            "target_node_id": job[5],
                            "command": job[6],
                            "result": result_data,
                            "created_by": job[8],
                            "created_at": job[9],
                            "started_at": job[10],
                            "completed_at": job[11]
                        })

                    conn.close()

                    self.send_json_response({
                        "tasks": job_list,
                        "total": len(job_list)
                    })

                elif path.startswith('/api/v1/nodes/') and 'heartbeat' in path:
                    # API v1节点心跳端点: /api/v1/nodes/{node_id}/heartbeat
                    parts = path.split('/')
                    node_id = parts[4] if len(parts) > 4 else 'unknown'

                    # 读取POST数据
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length)
                    try:
                        body_data = json.loads(post_data.decode('utf-8'))
                        node_id = body_data.get('node_id', node_id)
                    except:
                        pass

                    # 更新节点心跳
                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()

                    cursor.execute('SELECT * FROM nodes WHERE node_id = ?', (node_id,))
                    node = cursor.fetchone()

                    if node:
                        cursor.execute('''
                            UPDATE nodes SET
                                last_heartbeat = ?,
                                status = 'online',
                                updated_at = ?
                            WHERE node_id = ?
                        ''', (
                            datetime.now(timezone.utc).isoformat(),
                            datetime.now(timezone.utc).isoformat(),
                            node_id
                        ))
                        conn.commit()
                        conn.close()

                        self.send_json_response({
                            "status": "success",
                            "message": "Heartbeat received",
                            "node_id": node_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    else:
                        conn.close()
                        self.send_json_response({
                            "status": "error",
                            "message": "Node not found"
                        }, status=404)

                elif path.startswith('/api/v1/nodes/') and '/tasks/' in path and path.endswith('/result'):
                    # API v1任务结果端点: /api/v1/nodes/{node_id}/tasks/{task_id}/result
                    parts = path.split('/')
                    node_id = parts[4] if len(parts) > 4 else 'unknown'
                    task_id = parts[6] if len(parts) > 6 else 'unknown'

                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()

                    cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (task_id,))
                    job = cursor.fetchone()
                    conn.close()

                    if job:
                        try:
                            result_data = json.loads(job[7]) if job[7] else None
                        except:
                            result_data = None

                        self.send_json_response({
                            "task_id": task_id,
                            "node_id": node_id,
                            "status": job[4],
                            "result": result_data,
                            "completed_at": job[11]
                        })
                    else:
                        self.send_json_response({
                            "status": "error",
                            "message": "Task not found"
                        }, status=404)

'''

    # 在现有的/api/jobs端点之前插入API v1端点
    pattern = r"(elif path == '/api/jobs':)"

    if re.search(pattern, content):
        new_content = re.sub(pattern, api_v1_code + r"\1", content, count=1)

        if new_content != content:
            # 备份原文件
            backup_file(file_path)

            # 写入修改后的内容
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print("✅ API v1兼容端点已添加")
                print("📋 新增端点:")
                print("   - GET /api/v1/tasks")
                print("   - POST /api/v1/nodes/<node_id>/heartbeat")
                print("   - GET /api/v1/nodes/<node_id>/tasks/<task_id>/result")
                return True
            except Exception as e:
                print(f"❌ 写入文件失败: {e}")
                return False
        else:
            print("❌ 代码修改失败")
            return False
    else:
        print("❌ 未找到合适的插入点")
        return False

def main():
    if len(sys.argv) < 2:
        print("用法: python3 api_v1_patch.py <cloud_api_file_path>")
        print("示例: python3 api_v1_patch.py /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py")
        print("")
        print("默认路径: /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py")

        # 尝试默认路径
        default_path = "/home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py"
        if os.path.exists(default_path):
            print(f"\n🎯 发现默认路径文件，正在修复: {default_path}")
            if add_api_v1_endpoints(default_path):
                print("\n🎉 修复完成！请重启Cloud API服务使更改生效。")
                print("📋 重启命令:")
                print("   pkill -f v12_standard_cloud.py")
                print("   cd /home/scsun/hermesnexus-code")
                print("   nohup python3 cloud/api/v12_standard_cloud.py > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &")
                return 0
        else:
            print(f"\n❌ 默认路径文件不存在: {default_path}")
            return 1

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return 1

    if add_api_v1_endpoints(file_path):
        print("\n🎉 修复完成！请重启Cloud API服务使更改生效。")
        print("📋 重启命令:")
        print("   pkill -f v12_standard_cloud.py")
        print("   nohup python3 " + file_path + " > /home/scsun/hermesnexus-logs/cloud-api-v12.log 2>&1 &")
        return 0
    else:
        print("\n❌ 修复失败")
        return 1

if __name__ == '__main__':
    sys.exit(main())