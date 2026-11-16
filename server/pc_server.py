#!/usr/bin/env python3
"""
BlueVolume PC Companion Server
跨平台电脑端伴侣服务端 (支持 Windows, macOS, Linux)
支持通过 蓝牙 RFCOMM 或 本地网络 Socket 与 Android 客户端建立连接，
提供电脑操作系统识别、音量双向同步调节、远程关机功能。
"""

import os
import sys
import json
import time
import socket
import platform
import subprocess
import threading

def get_os_info():
    """获取详细的操作系统信息"""
    sys_name = platform.system()
    release = platform.release()
    node_name = platform.node()
    
    if sys_name == "Windows":
        os_type = "windows"
        pretty_name = f"Windows {release}"
    elif sys_name == "Darwin":
        os_type = "macos"
        mac_ver = platform.mac_ver()[0]
        pretty_name = f"macOS {mac_ver}" if mac_ver else "macOS"
    elif sys_name == "Linux":
        os_type = "linux"
        try:
            # 读取 /etc/os-release 获取发行版名称
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    lines = dict(line.strip().split("=", 1) for line in f if "=" in line)
                    pretty_name = lines.get("PRETTY_NAME", "Linux").strip('"')
            else:
                pretty_name = f"Linux ({release})"
        except Exception:
            pretty_name = f"Linux ({release})"
    else:
        os_type = "unknown"
        pretty_name = f"{sys_name} {release}"
        
    return {
        "os_type": os_type,       # "windows" | "macos" | "linux" | "unknown"
        "os_name": pretty_name,   # 人性化显示的操作系统名称
        "hostname": node_name     # 电脑主机名
    }

class AudioController:
    """跨平台音量控制器 (Windows / macOS / Linux)"""
    def __init__(self):
        self.os_type = get_os_info()["os_type"]
        self._init_windows_audio()

    def _init_windows_audio(self):
        self.win_volume_endpoint = None
        if self.os_type == "windows":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.win_volume_endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            except Exception as e:
                print(f"[Audio] Windows pycaw init failed (will use fallback): {e}")

    def get_volume(self) -> int:
        """获取当前音量 (0 - 100)"""
        try:
            if self.os_type == "windows":
                if self.win_volume_endpoint:
                    vol = self.win_volume_endpoint.GetMasterVolumeLevelScalar()
                    return int(round(vol * 100))
                # 兜底方式：通过 powershell 读取
                cmd = "powershell -Command \"[Math]::Round((Get-AudioDevice -PlaybackVolume).Percent)\""
                out = subprocess.check_output(cmd, shell=True, text=True, timeout=2).strip()
                return int(out) if out.isdigit() else 50
            elif self.os_type == "macos":
                out = subprocess.check_output(
                    ["osascript", "-e", "output volume of (get volume settings)"],
                    text=True, timeout=2
                ).strip()
                return int(out) if out.isdigit() else 50
            elif self.os_type == "linux":
                # 尝试 pactl
                try:
                    out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], text=True, timeout=2)
                    for part in out.split("/"):
                        part = part.strip()
                        if part.endswith("%"):
                            return int(part[:-1])
                except Exception:
                    pass
                # 尝试 amixer
                out = subprocess.check_output(["amixer", "sget", "Master"], text=True, timeout=2)
                import re
                m = re.search(r"\[([0-9]+)%\]", out)
                if m:
                    return int(m.group(1))
        except Exception as e:
            print(f"[Audio] get_volume failed: {e}")
        return 50

    def set_volume(self, volume: int):
        """设置当前音量 (0 - 100)"""
        volume = max(0, min(100, int(volume)))
        try:
            if self.os_type == "windows":
                if self.win_volume_endpoint:
                    self.win_volume_endpoint.SetMasterVolumeLevelScalar(volume / 100.0, None)
                else:
                    # 使用 PowerShell 调节音量 (通过音频端点接口或 nircmd)
                    ps_cmd = f"(new-object -com wscript.shell)" # 备用
                    # 若安装了 nircmd 或 NirCmdC
                    subprocess.run(f"powershell -Command \"[Audio]::SetMasterVolume({volume})\"", shell=True)
            elif self.os_type == "macos":
                subprocess.run(["osascript", "-e", f"set volume output volume {volume}"], timeout=2)
            elif self.os_type == "linux":
                # 尝试 pactl
                try:
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"], timeout=2)
                    return
                except Exception:
                    pass
                # 尝试 amixer
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{volume}%"], timeout=2)
        except Exception as e:
            print(f"[Audio] set_volume failed: {e}")

class SystemController:
    """跨平台关机执行器"""
    @staticmethod
    def shutdown():
        os_type = get_os_info()["os_type"]
        print(f"[System] Initiating shutdown for {os_type}...")
        try:
            if os_type == "windows":
                # 1秒倒计时安全关机
                os.system("shutdown /s /t 1")
            elif os_type == "macos":
                # 发送 AppleScript 关机指令
                os.system("osascript -e 'tell app \"System Events\" to shut down'")
            elif os_type == "linux":
                # 尝试 systemctl 或 poweroff
                if os.system("systemctl poweroff") != 0:
                    os.system("poweroff")
        except Exception as e:
            print(f"[System] Shutdown command failed: {e}")

class ConnectionHandler:
    """处理 Android 客户端连接会话与通信协议"""
    def __init__(self, sock, addr, audio_ctrl: AudioController):
        self.sock = sock
        self.addr = addr
        self.audio_ctrl = audio_ctrl
        self.running = True

    def handle(self):
        print(f"[Client] Connected from: {self.addr}")
        # 连接成功后先主动发送欢迎与初始系统信息
        self.send_system_info()

        buffer = ""
        try:
            while self.running:
                data = self.sock.recv(1024)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        self.process_message(line)
        except Exception as e:
            print(f"[Client] Connection error: {e}")
        finally:
            print(f"[Client] Disconnected: {self.addr}")
            try:
                self.sock.close()
            except Exception:
                pass

    def send_json(self, payload: dict):
        try:
            msg = json.dumps(payload) + "\n"
            self.sock.sendall(msg.encode("utf-8"))
        except Exception as e:
            print(f"[Client] Failed to send JSON: {e}")

    def send_system_info(self):
        info = get_os_info()
        curr_vol = self.audio_ctrl.get_volume()
        response = {
            "type": "SYSTEM_INFO",
            "os_type": info["os_type"],
            "os_name": info["os_name"],
            "hostname": info["hostname"],
            "volume": curr_vol
        }
        print(f"[Protocol] Sending system info: {response}")
        self.send_json(response)

    def process_message(self, raw_line: str):
        try:
            msg = json.loads(raw_line)
        except Exception:
            print(f"[Protocol] Non-JSON message received: {raw_line}")
            return

        msg_type = msg.get("type", "").upper()
        if msg_type == "GET_SYSTEM_INFO":
            self.send_system_info()

        elif msg_type == "SET_VOLUME":
            vol = msg.get("volume", 50)
            self.audio_ctrl.set_volume(vol)
            # 确认当前设置值
            self.send_json({"type": "VOLUME_CHANGED", "volume": vol})

        elif msg_type == "GET_VOLUME":
            vol = self.audio_ctrl.get_volume()
            self.send_json({"type": "VOLUME_CHANGED", "volume": vol})

        elif msg_type == "SHUTDOWN":
            print("[Protocol] Received confirmed SHUTDOWN request from Android app!")
            # 立即向手机回传确认
            self.send_json({"type": "SHUTDOWN_ACK", "status": "shutting_down"})
            # 延迟 1 秒以便数据包完全发送后再关机
            def delayed_shutdown():
                time.sleep(1.2)
                SystemController.shutdown()
            threading.Thread(target=delayed_shutdown, daemon=True).start()

        elif msg_type == "PING":
            self.send_json({"type": "PONG", "timestamp": time.time()})

def start_rfcomm_server(audio_ctrl: AudioController, channel=1):
    """启动经典蓝牙 RFCOMM 服务端 (Linux / 支持蓝牙的原生系统)"""
    try:
        server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        # 使用 00:00:00:00:00:00 绑定任意本地蓝牙控制器
        server_sock.bind(("00:00:00:00:00:00", channel))
        server_sock.listen(1)
        print(f"[Bluetooth] RFCOMM server listening on RFCOMM channel {channel}...")

        # 尝试注册 SDP 记录
        try:
            subprocess.run(["sdptool", "add", "SP"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        while True:
            client_sock, client_info = server_sock.accept()
            print(f"[Bluetooth] Accepted RFCOMM client: {client_info}")
            handler = ConnectionHandler(client_sock, client_info, audio_ctrl)
            threading.Thread(target=handler.handle, daemon=True).start()
    except Exception as e:
        print(f"[Bluetooth] RFCOMM initialization notice: {e}")
        print("[Bluetooth] RFCOMM requires local Bluetooth hardware and permissions.")

def start_tcp_server(audio_ctrl: AudioController, port=8888):
    """启动备用/通用的 TCP Socket 服务 (方便测试与蓝牙局域网联动)"""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", port))
    server_sock.listen(5)
    print(f"[TCP] Server listening on 0.0.0.0:{port} (WiFi / 蓝牙网络互联)")
    while True:
        client_sock, client_addr = server_sock.accept()
        handler = ConnectionHandler(client_sock, client_addr, audio_ctrl)
        threading.Thread(target=handler.handle, daemon=True).start()

def main():
    print("=" * 60)
    print(" BlueVolume PC Companion Agent ")
    print("=" * 60)
    info = get_os_info()
    print(f" Detected OS    : {info['os_name']} ({info['os_type']})")
    print(f" Hostname       : {info['hostname']}")
    
    audio_ctrl = AudioController()
    print(f" Current Volume : {audio_ctrl.get_volume()}%")
    print("=" * 60)

    # 启动 TCP 监听线程 (支持局域网或蓝牙共享网络)
    tcp_thread = threading.Thread(target=start_tcp_server, args=(audio_ctrl, 8888), daemon=True)
    tcp_thread.start()

    # 尝试启动原生蓝牙 RFCOMM 监听 (Linux / 支持的环境)
    if hasattr(socket, "AF_BLUETOOTH") and hasattr(socket, "BTPROTO_RFCOMM"):
        rfcomm_thread = threading.Thread(target=start_rfcomm_server, args=(audio_ctrl, 1), daemon=True)
        rfcomm_thread.start()
    else:
        print("[Notice] Python AF_BLUETOOTH not available on this platform, running in TCP/IP socket mode.")

    print("\n[Ready] Waiting for connection from Android App...")
    print("Press Ctrl+C to exit.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting server...")

if __name__ == "__main__":
    main()
