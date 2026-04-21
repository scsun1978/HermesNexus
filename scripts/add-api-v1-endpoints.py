#!/usr/bin/env python3
"""
直接在现有Cloud API中添加API v1兼容端点的补丁脚本
"""

import re
import sys
import os

def add_api_v1_compatibility(file_path):
    """在现有的Cloud API代码中添加API v1兼容端点"""

    # 读取现有代码
    with open(file_path, 'r') as f:
        code = f.read()

    # 检查是否已经包含API v1端点
    if 'api/v1/tasks' in code:
        print("✅ 代码已包含API v1兼容端点，无需添加")
        return True

    # 找到do_GET方法中的合适插入点（在现有的/api/jobs端点之前）
    # 我们需要在 elif path == '/api/jobs': 之前插入新的端点处理

    # 准备要插入的API v1兼容端点代码
    api_v1_endpoints = '''
                # API v1 兼容层 - 支持Edge节点的旧API格式
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

                elif path.startswith('/api/v1/nodes/') and path.endswith('/heartbeat'):
                    # API v1节点心跳端点: /api/v1/nodes/{node_id}/heartbeat
                    parts = path.split('/')
                    node_id = parts[4]

                    # 读取请求数据
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length)
                    try:
                        body_data = json.loads(post_data.decode('utf-8'))
                    except:
                        body_data = {}

                    node_id_from_body = body_data.get('node_id', node_id)

                    conn = sqlite3.connect(self.server_instance.db_path)
                    cursor = conn.cursor()

                    # 检查节点是否存在
                    cursor.execute('SELECT * FROM nodes WHERE node_id = ?', (node_id_from_body,))
                    node = cursor.fetchone()

                    if node:
                        # 更新心跳时间
                        cursor.execute('''
                            UPDATE nodes SET
                                last_heartbeat = ?,
                                status = 'online',
                                updated_at = ?
                            WHERE node_id = ?
                        ''', (datetime.now(timezone.utc).isoformat(),
                              datetime.now(timezone.utc).isoformat(),
                              node_id_from_body))

                        conn.commit()
                        conn.close()

                        self.send_json_response({
                            "status": "success",
                            "message": "Heartbeat received",
                            "node_id": node_id_from_body,
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
                    node_id = parts[4]
                    task_id = parts[6]

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

    # 找到插入点 - 在现有的 elif path == '/api/jobs': 之前插入
    insert_pattern = r"(elif path == '/api/jobs':)"
    replacement = api_v1_endpoints + r"\1"

    new_code = re.sub(insert_pattern, replacement, code, count=1)

    if new_code == code:
        print("❌ 未找到合适的插入点，可能代码结构已改变")
        return False

    # 备份原文件
    backup_path = file_path + '.backup.' + str(int(os.path.getmtime(file_path)))
    with open(backup_path, 'w') as f:
        f.write(code)
    print(f"✅ 原文件已备份: {backup_path}")

    # 写入新代码
    with open(file_path, 'w') as f:
        f.write(new_code)

    print("✅ API v1兼容端点已添加")
    return True

def main():
    if len(sys.argv) < 2:
        print("用法: python3 add-api-v1-endpoints.py <cloud_api_file_path>")
        print("示例: python3 add-api-v1-endpoints.py /home/scsun/hermesnexus-code/cloud/api/v12_standard_cloud.py")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)

    print(f"🔧 正在修复: {file_path}")

    if add_api_v1_compatibility(file_path):
        print("🎉 修复完成！")
        print(f"📋 已添加以下API v1兼容端点:")
        print(f"   - GET /api/v1/tasks")
        print(f"   - POST /api/v1/nodes/<node_id>/heartbeat")
        print(f"   - GET /api/v1/nodes/<node_id>/tasks/<task_id>/result")
        print(f"\n🔄 请重启Cloud API服务使更改生效")
    else:
        print("❌ 修复失败")
        sys.exit(1)

if __name__ == '__main__':
    main()