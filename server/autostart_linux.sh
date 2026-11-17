#!/usr/bin/env bash
# BlueVolume Linux 开机自启动安装/卸载脚本 (基于 systemd --user)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PY="$SCRIPT_DIR/pc_server.py"
PYTHON_BIN="$(which python3)"
SERVICE_NAME="bluevolume.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$USER_SYSTEMD_DIR/$SERVICE_NAME"

action="${1:-install}"

install_service() {
    echo "=================================================="
    echo " 安装 BlueVolume 开机自启动服务 (systemd --user)"
    echo "=================================================="
    echo "Python 路径: $PYTHON_BIN"
    echo "脚本路径  : $SERVER_PY"
    echo "服务文件  : $SERVICE_FILE"

    mkdir -p "$USER_SYSTEMD_DIR"

    cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=BlueVolume PC Companion Server
After=network.target sound.target default.target
Wants=sound.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_BIN $SERVER_PY
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1
Environment=PATH=/usr/local/bin:/usr/bin:/bin:$PATH
Environment=XDG_RUNTIME_DIR=/run/user/%U

[Install]
WantedBy=default.target
EOF

    # 启用用户常驻守护 (即使未登录图形界面，开机即启动)
    loginctl enable-linger "$(whoami)" 2>/dev/null || true

    echo "[1/4] 重新加载 systemd 用户配置..."
    systemctl --user daemon-reload

    echo "[2/4] 设置开机自启动..."
    systemctl --user enable "$SERVICE_NAME"

    echo "[3/4] 启动服务..."
    systemctl --user restart "$SERVICE_NAME"

    echo "[4/4] 检查服务状态..."
    sleep 1
    if systemctl --user is-active --quiet "$SERVICE_NAME"; then
        echo "=================================================="
        echo "✅ 成功！BlueVolume 已启动并在开机时自动运行！"
        echo "查看实时日志: journalctl --user -u $SERVICE_NAME -f"
        echo "停止自启服务: $0 uninstall"
        echo "=================================================="
    else
        echo "❌ 服务启动异常，请运行检查: systemctl --user status $SERVICE_NAME"
        exit 1
    fi
}

uninstall_service() {
    echo "=================================================="
    echo " 卸载 BlueVolume 开机自启动服务"
    echo "=================================================="
    systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo "✅ 已成功停止并移除开机自启动服务！"
}

case "$action" in
    install)
        install_service
        ;;
    uninstall|remove)
        uninstall_service
        ;;
    status)
        systemctl --user status "$SERVICE_NAME"
        ;;
    restart)
        systemctl --user restart "$SERVICE_NAME"
        ;;
    logs)
        journalctl --user -u "$SERVICE_NAME" -f
        ;;
    *)
        echo "用法: $0 [install|uninstall|status|restart|logs]"
        exit 1
        ;;
esac
