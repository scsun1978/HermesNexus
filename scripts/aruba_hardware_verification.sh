#!/bin/bash
# Aruba 真机硬件验证辅助脚本
# 自动化网络连接测试和结果收集

set -e

ARUBA_DEVICE="172.16.200.21"
ARUBA_USER="admin"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="aruba_verification_${TIMESTAMP}.log"

echo "🚀 Aruba真机硬件验证辅助脚本"
echo "=================================="
echo "目标设备: ${ARUBA_DEVICE}"
echo "验证时间: $(date)"
echo "日志文件: ${LOG_FILE}"
echo ""

# 创建日志文件
exec > >(tee -a "${LOG_FILE}") 2>&1

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试函数
test_network_connectivity() {
    echo "📡 Step 1: 网络连通性测试"
    echo "---------------------------"

    # Ping测试
    echo -n "Ping测试... "
    if ping -c 3 -W 5 ${ARUBA_DEVICE} > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 成功${NC}"
        ping -c 3 ${ARUBA_DEVICE} | grep "round-trip"
    else
        echo -e "${RED}❌ 失败${NC}"
        return 1
    fi

    # SSH端口测试
    echo -n "SSH端口测试 (22)... "
    if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${ARUBA_DEVICE}/22" 2>/dev/null; then
        echo -e "${GREEN}✅ 开放${NC}"
    else
        echo -e "${RED}❌ 关闭或不可达${NC}"
        return 1
    fi

    echo ""
}

test_ssh_connection() {
    echo "🔐 Step 2: SSH连接测试"
    echo "---------------------------"

    echo -n "SSH连接测试... "

    # 使用sshpass如果可用，否则提示手动输入
    if command -v sshpass &> /dev/null; then
        if sshpass -p "aruba123" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
            ${ARUBA_USER}@${ARUBA_DEVICE} "exit" 2>/dev/null; then
            echo -e "${GREEN}✅ 自动连接成功${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️ 自动连接失败，可能需要手动验证${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️ 需要手动SSH连接验证${NC}"
        echo "   请手动执行: ssh ${ARUBA_USER}@${ARUBA_DEVICE}"
        return 1
    fi

    echo ""
}

execute_remote_command() {
    local command=$1
    local description=$2

    echo "执行: ${description}"
    echo "命令: ${command}"

    if command -v sshpass &> /dev/null; then
        echo "结果:"
        sshpass -p "aruba123" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
            ${ARUBA_USER}@${ARUBA_DEVICE} "${command}" 2>/dev/null || echo "命令执行失败"
    else
        echo "⚠️ 请手动执行上述命令并记录结果"
    fi

    echo "-------------------------------------------"
    echo ""
}

run_verification_commands() {
    echo "🔍 Step 3: Aruba命令验证"
    echo "---------------------------"
    echo ""

    # 基础命令验证
    echo "📋 阶段1: 基础命令验证"
    execute_remote_command "show version" "设备版本信息"
    execute_remote_command "show ap database" "AP数据库 (Aruba特有)"
    execute_remote_command "show client summary" "客户端摘要 (Aruba特有)"
    execute_remote_command "show interface brief" "接口状态 (命令适配映射)"

    # 配置管理验证
    echo "📋 阶段2: 配置管理验证"
    execute_remote_command "show running-config | include hostname" "运行配置 (部分显示)"
    execute_remote_command "write memory" "配置保存 (命令适配映射)"

    # 高级功能验证
    echo "📋 阶段3: 高级功能验证"
    execute_remote_command "show version && show ap database" "命令组合测试"
    execute_remote_command "ping -c 3 8.8.8.8" "网络连通性测试"

    # Aruba模板验证
    echo "📋 阶段4: Aruba模板验证"
    execute_remote_command "show version && show ap database && show client summary" "Aruba巡检模板"
}

collect_device_info() {
    echo "📊 Step 4: 设备信息收集"
    echo "---------------------------"

    if command -v sshpass &> /dev/null; then
        echo "收集详细设备信息..."
        sshpass -p "aruba123" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
            ${ARUBA_USER}@${ARUBA_DEVICE} "
            echo '=== 设备系统信息 ==='
            show system
            echo ''
            echo '=== 设备版本信息 ==='
            show version
            echo ''
            echo '=== IP接口信息 ==='
            show ip interface
            echo ''
            echo '=== ARP表 ==='
            show arp
        " 2>/dev/null || echo "信息收集失败"
    else
        echo "⚠️ 请手动收集设备信息"
    fi

    echo ""
}

generate_summary_report() {
    echo "📝 Step 5: 生成验证总结"
    echo "---------------------------"

    cat << 'EOF'
=== Aruba真机验证总结 ===

验证状态: ☐ 待完成  ☐ 进行中  ✅ 已完成

网络连接: ☐ 成功  ☐ 失败
SSH连接: ☐ 成功  ☐ 失败  ☐ 需手动验证
命令执行: ☐ 正常  ☐ 异常

核心功能:
- 设备信息查询:    ☐ 正常  ☐ 异常
- Aruba特有命令:    ☐ 正常  ☐ 异常
- 命令适配映射:     ☐ 正常  ☐ 异常
- 配置管理:         ☐ 正常  ☐ 异常
- 组合命令:         ☐ 正常  ☐ 异常

Phase 4B验证:
- 命令适配器:       ☐ 通过  ☐ 失败
- Aruba模板:        ☐ 通过  ☐ 失败
- 设备支持:         ☐ 通过  ☐ 失败

生产就绪评估:
- 功能完整性:       ☐ 完成  ☐ 部分完成  ☐ 未完成
- 性能表现:         ☐ 达标  ☐ 需优化
- 稳定性:           ☐ 稳定  ☐ 需改进
- 兼容性:           ☐ 兼容  ☐ 有问题

最终建议:
☐ 生产就绪 - 可以部署
☐ 需要修复 - 修复后部署
☐ 不推荐 - 需要重大改进

备注:
[记录重要发现和问题]

=======================
EOF

    echo ""
}

manual_verification_instructions() {
    echo "👤 手动验证指南"
    echo "---------------------------"
    cat << 'EOF'

由于SSH自动连接可能受限，请按以下步骤手动验证：

1. 手动SSH连接:
   ssh admin@172.16.200.21
   (输入密码: aruba123)

2. 执行核心验证命令:
   - show version
   - show ap database
   - show client summary
   - show interface brief
   - write memory
   - show version && show ap database

3. 观察每个命令的:
   ✅ 执行是否成功
   ✅ 输出格式是否正确
   ✅ 响应时间是否正常
   ✅ 错误处理是否恰当

4. 使用快速参考卡:
   参考 docs/references/2026-04-21-aruba-verification-quick-reference.md

5. 记录验证结果:
   填写 docs/reports/2026-04-21-aruba-hardware-verification-results.md

EOF
    echo ""
}

# 主执行流程
main() {
    echo "开始Aruba真机硬件验证..."
    echo ""

    # Step 1: 网络测试
    if test_network_connectivity; then
        echo -e "${GREEN}✅ 网络连接正常${NC}"
    else
        echo -e "${RED}❌ 网络连接失败，请检查设备状态${NC}"
        exit 1
    fi

    # Step 2: SSH测试
    if test_ssh_connection; then
        echo -e "${GREEN}✅ SSH连接正常${NC}"
        HAS_SSH=true
    else
        echo -e "${YELLOW}⚠️ SSH需要手动验证${NC}"
        HAS_SSH=false
    fi

    # Step 3-5: 如果有自动SSH，执行命令验证
    if [ "$HAS_SSH" = true ]; then
        run_verification_commands
        collect_device_info
    else
        manual_verification_instructions
    fi

    # Step 6: 生成总结报告
    generate_summary_report

    echo "=================================="
    echo -e "${GREEN}✅ 验证脚本执行完成${NC}"
    echo "详细日志: ${LOG_FILE}"
    echo ""
    echo "📋 后续步骤:"
    echo "1. 查看日志文件: cat ${LOG_FILE}"
    echo "2. 填写验证结果: docs/reports/2026-04-21-aruba-hardware-verification-results.md"
    echo "3. 如需手动验证，参考指南: docs/guides/2026-04-21-aruba-hardware-manual-verification-guide.md"
    echo "4. 使用快速参考卡: docs/references/2026-04-21-aruba-verification-quick-reference.md"
}

# 执行主函数
main "$@"