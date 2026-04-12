#!/bin/bash
# HermesNexus 数据备份脚本
# 支持SQLite数据库的自动备份和恢复

set -e

# 配置变量
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATA_DIR="${DATA_DIR:-./data}"
DB_FILE="${SQLITE_DB_PATH:-./data/hermesnexus.db}"
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 创建备份目录
ensure_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_success "✅ 创建备份目录: $BACKUP_DIR"
    fi
}

# 获取时间戳
get_timestamp() {
    date +"%Y%m%d_%H%M%S"
}

# 备份SQLite数据库
backup_sqlite() {
    log_info "🗄️  开始备份SQLite数据库..."

    if [ ! -f "$DB_FILE" ]; then
        log_error "❌ 数据库文件不存在: $DB_FILE"
        return 1
    fi

    local timestamp=$(get_timestamp)
    local backup_file="$BACKUP_DIR/hermesnexus_${timestamp}.db"
    local compressed_file="${backup_file}.gz"

    # 复制数据库文件
    cp "$DB_FILE" "$backup_file"

    # 压缩备份文件
    if command_exists gzip; then
        gzip "$backup_file"
        backup_file="$compressed_file"
        log_success "✅ 数据库备份已压缩"
    fi

    # 计算校验和
    local checksum=$(sha256sum "$backup_file" | awk '{print $1}')
    echo "$checksum" > "${backup_file}.sha256"

    # 记录备份元数据
    local backup_meta="$BACKUP_DIR/backup_${timestamp}.meta"
    cat > "$backup_meta" << EOF
backup_time=$(date -Iseconds)
backup_file=$backup_file
backup_size=$(wc -c < "$backup_file")
backup_checksum=$checksum
db_size=$(wc -c < "$DB_FILE")
EOF

    log_success "✅ 数据库备份完成: $backup_file"
    log_info "📊 备份信息:"
    echo "  文件大小: $(du -h "$backup_file" | cut -f1)"
    echo "  校验和: $checksum"

    return 0
}

# 备份配置文件
backup_configs() {
    log_info "📝 开始备份配置文件..."

    local timestamp=$(get_timestamp)
    local config_backup="$BACKUP_DIR/configs_${timestamp}.tar.gz"

    # 创建配置备份
    if [ -f .env ]; then
        tar -czf "$config_backup" .env 2>/dev/null || true
        log_success "✅ 配置文件备份完成: $config_backup"
    fi
}

# 备份日志文件
backup_logs() {
    log_info "📋 开始备份日志文件..."

    local timestamp=$(get_timestamp)
    local log_backup="$BACKUP_DIR/logs_${timestamp}.tar.gz"

    if [ -d "$LOG_DIR" ]; then
        tar -czf "$log_backup" -C "$LOG_DIR" . 2>/dev/null || true
        log_success "✅ 日志文件备份完成: $log_backup"
    fi
}

# 清理过期备份
cleanup_old_backups() {
    log_info "🧹 清理过期备份文件..."

    if [ ! -d "$BACKUP_DIR" ]; then
        return 0
    fi

    # 查找并删除过期的数据库备份
    find "$BACKUP_DIR" -name "hermesnexus_*.db.gz" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "hermesnexus_*.db.sha256" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true

    # 清理过期的配置备份
    find "$BACKUP_DIR" -name "configs_*.tar.gz" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true

    # 清理过期的日志备份
    find "$BACKUP_DIR" -name "logs_*.tar.gz" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true

    log_success "✅ 过期备份清理完成 (保留${BACKUP_RETENTION_DAYS}天)"
}

# 列出所有备份
list_backups() {
    log_info "📋 现有备份文件:"

    if [ ! -d "$BACKUP_DIR" ]; then
        log_warning "⚠️  备份目录不存在"
        return 1
    fi

    echo ""
    echo "数据库备份:"
    find "$BACKUP_DIR" -name "hermesnexus_*.db.gz" -type f -exec ls -lh {} \; | awk '{print $9, "(" $5 ")"}'

    echo ""
    echo "配置备份:"
    find "$BACKUP_DIR" -name "configs_*.tar.gz" -type f -exec ls -lh {} \; | awk '{print $9, "(" $5 ")"}'

    echo ""
    echo "日志备份:"
    find "$BACKUP_DIR" -name "logs_*.tar.gz" -type f -exec ls -lh {} \; | awk '{print $9, "(" $5 ")"}'
}

# 验证备份完整性
verify_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "❌ 备份文件不存在: $backup_file"
        return 1
    fi

    log_info "🔍 验证备份完整性: $backup_file"

    # 检查校验和
    if [ -f "${backup_file}.sha256" ]; then
        local stored_checksum=$(cat "${backup_file}.sha256}" | awk '{print $1}')
        local current_checksum=$(sha256sum "$backup_file" | awk '{print $1}')

        if [ "$stored_checksum" = "$current_checksum" ]; then
            log_success "✅ 校验和验证通过"
        else
            log_error "❌ 校验和不匹配，备份可能已损坏"
            return 1
        fi
    fi

    # 如果是压缩文件，测试解压
    if [[ "$backup_file" == *.gz ]]; then
        if command_exists gzip; then
            if gzip -t "$backup_file" 2>/dev/null; then
                log_success "✅ 压缩文件验证通过"
            else
                log_error "❌ 压缩文件损坏"
                return 1
            fi
        fi
    fi

    log_success "✅ 备份验证通过"
    return 0
}

# 恢复数据库
restore_database() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "❌ 备份文件不存在: $backup_file"
        return 1
    fi

    log_warning "⚠️  即将恢复数据库，当前数据将被覆盖"
    read -p "确认恢复? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "取消恢复操作"
        return 0
    fi

    log_info "🔄 开始恢复数据库..."

    # 停止服务
    log_info "停止相关服务..."
    pkill -f "python.*cloud/api/main.py" || true
    sleep 2

    # 备份当前数据库
    if [ -f "$DB_FILE" ]; then
        local current_backup="$DB_FILE.before_restore"
        cp "$DB_FILE" "$current_backup"
        log_info "当前数据库已备份到: $current_backup"
    fi

    # 解压并恢复
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" > "$DB_FILE"
    else
        cp "$backup_file" "$DB_FILE"
    fi

    # 重启服务
    log_info "重启服务..."
    cd "$PROJECT_ROOT"
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    source venv/bin/activate
    python cloud/api/main.py > /dev/null 2>&1 &
    sleep 3

    log_success "✅ 数据库恢复完成"
    log_info "请验证系统功能是否正常"
}

# 完整备份 (数据库+配置+日志)
full_backup() {
    log_info "🚀 开始完整备份..."

    ensure_backup_dir
    backup_sqlite
    backup_configs
    backup_logs
    cleanup_old_backups

    log_success "🎉 完整备份完成！"
}

# 定时备份设置
setup_cron_backup() {
    local cron_schedule="${1:-0 2 * * *}"  # 默认每天凌晨2点

    log_info "⏰ 设置定时备份: $cron_schedule"

    # 检查crontab
    if ! command_exists crontab; then
        log_error "❌ crontab命令不存在，无法设置定时任务"
        return 1
    fi

    # 添加cron任务
    local backup_script="$PROJECT_ROOT/scripts/backup.sh"
    local cron_job="$cron_schedule $backup_script full >/dev/null 2>&1"

    # 检查是否已存在
    if crontab -l 2>/dev/null | grep -q "$backup_script"; then
        log_warning "⚠️  定时备份任务已存在，跳过添加"
    else
        (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
        log_success "✅ 定时备份任务已添加"
    fi

    log_info "查看定时任务: crontab -l"
}

# 显示备份统计
backup_statistics() {
    log_info "📊 备份统计信息:"

    if [ ! -d "$BACKUP_DIR" ]; then
        log_warning "⚠️  备份目录不存在"
        return 1
    fi

    local total_backups=$(find "$BACKUP_DIR" -name "hermesnexus_*.db.gz" | wc -l)
    local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    local oldest=$(find "$BACKUP_DIR" -name "hermesnexus_*.db.gz" -type f | sort -r | tail -1)
    local newest=$(find "$BACKUP_DIR" -name "hermesnexus_*.db.gz" -type f | sort | tail -1)

    echo ""
    echo "备份总数: $total_backups"
    echo "总大小: $total_size"
    echo "最新备份: $(basename "$newest")"
    echo "最旧备份: $(basename "$oldest")"
}

# 主函数
main() {
    local action="${1:-full}"

    case "$action" in
        full)
            full_backup
            ;;
        db)
            ensure_backup_dir
            backup_sqlite
            ;;
        configs)
            ensure_backup_dir
            backup_configs
            ;;
        logs)
            ensure_backup_dir
            backup_logs
            ;;
        list)
            list_backups
            ;;
        verify)
            if [ -z "$2" ]; then
                log_error "❌ 请指定要验证的备份文件"
                exit 1
            fi
            verify_backup "$2"
            ;;
        restore)
            if [ -z "$2" ]; then
                log_error "❌ 请指定要恢复的备份文件"
                exit 1
            fi
            restore_database "$2"
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        cron)
            setup_cron_backup "$2"
            ;;
        stats)
            backup_statistics
            ;;
        *)
            echo "用法: $0 {full|db|configs|logs|list|verify|restore|cleanup|cron|stats}"
            echo ""
            echo "命令说明:"
            echo "  full    - 完整备份 (数据库+配置+日志)"
            echo "  db      - 仅备份数据库"
            echo "  configs - 仅备份配置文件"
            echo "  logs    - 仅备份日志文件"
            echo "  list    - 列出所有备份文件"
            echo "  verify  - 验证备份完整性"
            echo "  restore - 恢复数据库"
            echo "  cleanup - 清理过期备份"
            echo "  cron    - 设置定时备份"
            echo "  stats   - 显示备份统计"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"