#!/usr/bin/env python3
"""
为Cloud API添加API v1 POST heartbeat端点
"""

def add_api_v1_post_heartbeat(file_path):
    """在Cloud API的do_POST方法中添加API v1 heartbeat端点"""

    with open(file_path, 'r') as f:
        content = f.read()

    # API v1 POST heartbeat端点代码
    api_v1_post_code = '''            # API v1兼容层 - 节点心跳端点
            if path.startswith('/api/v1/nodes/') and path.endswith('/heartbeat'):
                parts = path.split('/')
                node_id = parts[4] if len(parts) > 4 else 'unknown'
                node_id = body.get('node_id', node_id)

                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()

                # 检查节点是否存在
                cursor.execute('SELECT * FROM nodes WHERE node_id = ?', (node_id,))
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
                          node_id))
                    conn.commit()
                    conn.close()

                    self.send_json_response({
                        "status": "success",
                        "message": "Heartbeat received",
                        "node_id": node_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    # 如果节点不存在，创建新节点
                    cursor.execute('''
                        INSERT INTO nodes
                        (node_id, node_type, hostname, ip_address, port, status, last_heartbeat, capabilities, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (node_id, 'edge', socket.gethostname(), '127.0.0.1', 8081, 'online',
                          datetime.now(timezone.utc).isoformat(),
                          json.dumps({}), json.dumps({}),
                          datetime.now(timezone.utc).isoformat(),
                          datetime.now(timezone.utc).isoformat()))
                    conn.commit()
                    conn.close()

                    self.send_json_response({
                        "status": "success",
                        "message": "Node registered and heartbeat received",
                        "node_id": node_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

'''

    # 在do_POST方法中的节点注册端点之前插入
    pattern = r"(            if path == '/api/nodes/register':)"
    new_content = re.sub(pattern, api_v1_post_code + r"\1", content, count=1)

    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        return True
    else:
        return False

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = '/home/scsun/hermesnexus-v12/cloud-api-v12.py'

    if add_api_v1_post_heartbeat(file_path):
        print("✅ API v1 POST heartbeat端点已添加")
    else:
        print("❌ 添加失败")