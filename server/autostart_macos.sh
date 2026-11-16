#!/usr/bin/env bash
# BlueVolume macOS 开机自启动配置脚本 (基于 LaunchAgents)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PY="$SCRIPT_DIR/pc_server.py"
PYTHON_BIN="$(which python3)"
PLIST_NAME="com.realsky.bluevolume.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

action="${1:-install}"

if [ "$action" = "uninstall" ] || [ "$action" = "remove" ]; then
    echo "正在卸载 macOS 开机自启项..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "✅ 已成功移除！"
    exit 0
fi

echo "=================================================="
echo " 正在安装 BlueVolume macOS 开机自启动服务"
echo "=================================================="
mkdir -p "$HOME/Library/LaunchAgents"

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.realsky.bluevolume</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$SERVER_PY</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>StandardOutPath</key>
    <string>/tmp/bluevolume.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/bluevolume.err</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✅ 成功！BlueVolume 已设置为 macOS 登录自启动并在后台守护运行！"
echo "日志文件位置: /tmp/bluevolume.log"
echo "卸载命令: $0 uninstall"
