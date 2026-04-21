/**
 * HermesNexus Unified Notification System
 * 统一通知系统 - 提供一致的错误处理和用户反馈
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.maxNotifications = 5;
        this.defaultDuration = 3000; // 3 seconds
        this.init();
    }

    init() {
        // Create notification container if it doesn't exist
        this.container = document.getElementById('notification-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notification-container';
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);

            // Add styles if not already present
            this.addStyles();
        }
    }

    addStyles() {
        if (document.getElementById('notification-styles')) return;

        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
                pointer-events: none;
            }

            .notification {
                background: white;
                border-left: 4px solid #ccc;
                border-radius: 4px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                margin-bottom: 10px;
                padding: 16px;
                pointer-events: auto;
                animation: slideIn 0.3s ease-out;
                display: flex;
                align-items: center;
                justify-content: space-between;
                min-height: 50px;
            }

            .notification.success {
                border-left-color: #52c41a;
            }

            .notification.error {
                border-left-color: #ff4d4f;
            }

            .notification.warning {
                border-left-color: #faad14;
            }

            .notification.info {
                border-left-color: #1890ff;
            }

            .notification.loading {
                border-left-color: #1890ff;
            }

            .notification-content {
                flex: 1;
                margin-right: 10px;
            }

            .notification-title {
                font-weight: 600;
                margin-bottom: 4px;
                color: #333;
            }

            .notification-message {
                color: #666;
                font-size: 14px;
            }

            .notification-close {
                background: none;
                border: none;
                color: #999;
                cursor: pointer;
                font-size: 18px;
                padding: 0;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background-color 0.2s;
            }

            .notification-close:hover {
                background-color: #f0f0f0;
                color: #333;
            }

            .notification-icon {
                margin-right: 12px;
                font-size: 20px;
            }

            .notification.loading .notification-icon {
                animation: spin 1s linear infinite;
            }

            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }

            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            .notification.removing {
                animation: slideOut 0.3s ease-out forwards;
            }
        `;
        document.head.appendChild(style);
    }

    show(options) {
        const {
            type = 'info',
            title = '',
            message = '',
            duration = this.defaultDuration,
            closable = true,
            icon = true
        } = options;

        // Remove oldest notifications if we exceed max
        while (this.notifications.length >= this.maxNotifications) {
            this.remove(this.notifications[0].id);
        }

        const notification = document.createElement('div');
        const notificationId = `notification-${Date.now()}-${Math.random()}`;
        notification.id = notificationId;
        notification.className = `notification ${type}`;

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
            loading: '⟳'
        };

        let iconHtml = icon ? `<span class="notification-icon">${icons[type] || icons.info}</span>` : '';

        notification.innerHTML = `
            ${iconHtml}
            <div class="notification-content">
                ${title ? `<div class="notification-title">${this.escapeHtml(title)}</div>` : ''}
                ${message ? `<div class="notification-message">${this.escapeHtml(message)}</div>` : ''}
            </div>
            ${closable ? '<button class="notification-close" onclick="notificationSystem.remove(\'' + notificationId + '\')">&times;</button>' : ''}
        `;

        this.container.appendChild(notification);

        const notificationData = {
            id: notificationId,
            element: notification,
            timeout: null
        };

        this.notifications.push(notificationData);

        // Auto-remove after duration (except for loading notifications)
        if (duration > 0 && type !== 'loading') {
            notificationData.timeout = setTimeout(() => {
                this.remove(notificationId);
            }, duration);
        }

        return notificationId;
    }

    remove(notificationId) {
        const index = this.notifications.findIndex(n => n.id === notificationId);
        if (index !== -1) {
            const notificationData = this.notifications[index];

            if (notificationData.timeout) {
                clearTimeout(notificationData.timeout);
            }

            notificationData.element.classList.add('removing');

            setTimeout(() => {
                if (notificationData.element.parentNode) {
                    notificationData.element.parentNode.removeChild(notificationData.element);
                }
            }, 300); // Wait for animation to complete

            this.notifications.splice(index, 1);
        }
    }

    success(message, title = '成功', duration = 3000) {
        return this.show({
            type: 'success',
            title,
            message,
            duration
        });
    }

    error(message, title = '错误', duration = 5000) {
        return this.show({
            type: 'error',
            title,
            message,
            duration
        });
    }

    warning(message, title = '警告', duration = 4000) {
        return this.show({
            type: 'warning',
            title,
            message,
            duration
        });
    }

    info(message, title = '提示', duration = 3000) {
        return this.show({
            type: 'info',
            title,
            message,
            duration
        });
    }

    loading(message, title = '加载中') {
        return this.show({
            type: 'loading',
            title,
            message,
            duration: 0, // Don't auto-remove loading notifications
            closable: false
        });
    }

    clear() {
        // Remove all notifications
        [...this.notifications].forEach(notification => {
            this.remove(notification.id);
        });
    }

    escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) {
            return '';
        }
        return String(unsafe)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Global instance
const notificationSystem = new NotificationSystem();

// Convenience functions for backward compatibility
function showSuccess(message, title) {
    return notificationSystem.success(message, title);
}

function showError(message, title) {
    return notificationSystem.error(message, title);
}

function showWarning(message, title) {
    return notificationSystem.warning(message, title);
}

function showInfo(message, title) {
    return notificationSystem.info(message, title);
}

function showLoading(message, title) {
    return notificationSystem.loading(message, title);
}

function hideLoading(notificationId) {
    if (notificationId) {
        notificationSystem.remove(notificationId);
    } else {
        // Remove all loading notifications
        notificationSystem.notifications.forEach(notification => {
            const element = notification.element;
            if (element.classList.contains('loading')) {
                notificationSystem.remove(notification.id);
            }
        });
    }
}