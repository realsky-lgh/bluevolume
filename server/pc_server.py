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
        self._win_use_com = False
        if self.os_type == "windows":
            # 1. 优先尝试 pycaw
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.win_volume_endpoint = cast(interface, POINTER(IAudioEndpointVolume))
                return
            except Exception:
                pass

            # 2. 如果没有 pycaw，通过 comtypes + WASAPI COM 接口直接原生调用（无需安装额外包）
            try:
                from ctypes import wintypes, POINTER, c_float, c_long, c_ulong
                from comtypes import IUnknown, GUID, COMMETHOD

                class IAudioEndpointVolume(IUnknown):
                    _iid_ = GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')
                    _methods_ = [
                        COMMETHOD([], c_long, 'RegisterControlChangeNotify', (['in'], POINTER(IUnknown), 'pNotify')),
                        COMMETHOD([], c_long, 'UnregisterControlChangeNotify', (['in'], POINTER(IUnknown), 'pNotify')),
                        COMMETHOD([], c_long, 'GetChannelCount', (['out'], POINTER(c_ulong), 'pnChannelCount')),
                        COMMETHOD([], c_long, 'SetMasterVolumeLevel', (['in'], c_float, 'fLevelDB'), (['in'], POINTER(GUID), 'pguidEventContext')),
                        COMMETHOD([], c_long, 'SetMasterVolumeLevelScalar', (['in'], c_float, 'fLevel'), (['in'], POINTER(GUID), 'pguidEventContext')),
                        COMMETHOD([], c_long, 'GetMasterVolumeLevel', (['out'], POINTER(c_float), 'pfLevelDB')),
                        COMMETHOD([], c_long, 'GetMasterVolumeLevelScalar', (['out'], POINTER(c_float), 'pfLevel')),
                        COMMETHOD([], c_long, 'SetMute', (['in'], wintypes.BOOL, 'bMute'), (['in'], POINTER(GUID), 'pguidEventContext')),
                        COMMETHOD([], c_long, 'GetMute', (['out'], POINTER(wintypes.BOOL), 'pbMute')),
                    ]

                class IMMDevice(IUnknown):
                    _iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
                    _methods_ = [
                        COMMETHOD([], c_long, 'Activate', (['in'], POINTER(GUID), 'iid'), (['in'], c_ulong, 'dwClsCtx'), (['in'], POINTER(c_long), 'pActivationParams'), (['out'], POINTER(POINTER(IUnknown)), 'ppInterface')),
                    ]

                class IMMDeviceEnumerator(IUnknown):
                    _iid_ = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
                    _methods_ = [
                        COMMETHOD([], c_long, 'EnumAudioEndpoints'),
                        COMMETHOD([], c_long, 'GetDefaultAudioEndpoint', (['in'], c_long, 'dataFlow'), (['in'], c_long, 'role'), (['out'], POINTER(POINTER(IMMDevice)), 'ppDevice')),
                    ]

                self._IAudioEndpointVolume = IAudioEndpointVolume
                self._IMMDeviceEnumerator = IMMDeviceEnumerator
                self._CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
                self._IID_IAudioEndpointVolume = GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')
                self._win_use_com = True
            except Exception as e:
                print(f"[Audio] Windows COM fallback init notice: {e}")

    def _get_win_com_endpoint(self):
        """为当前线程创建/获取 Windows 音量控制 COM 接口"""
        if not getattr(self, "_win_use_com", False):
            return None
        import comtypes
        from comtypes import CoInitialize, CoCreateInstance, CLSCTX_INPROC_SERVER
        try:
            CoInitialize()
        except Exception:
            pass
        de = CoCreateInstance(self._CLSID_MMDeviceEnumerator, interface=self._IMMDeviceEnumerator, clsctx=CLSCTX_INPROC_SERVER)
        dev = de.GetDefaultAudioEndpoint(0, 1)  # eRender=0, eMultimedia=1
        endpoint = dev.Activate(self._IID_IAudioEndpointVolume, CLSCTX_INPROC_SERVER, None)
        return endpoint.QueryInterface(self._IAudioEndpointVolume)

    def get_volume(self) -> int:
        """获取当前音量 (0 - 100)"""
        try:
            if self.os_type == "windows":
                if self.win_volume_endpoint:
                    vol = self.win_volume_endpoint.GetMasterVolumeLevelScalar()
                    return int(round(vol * 100))
                endpoint = self._get_win_com_endpoint()
                if endpoint:
                    vol = endpoint.GetMasterVolumeLevelScalar()
                    return int(round(vol * 100))
                return 50
            elif self.os_type == "macos":
                out = subprocess.check_output(
                    ["osascript", "-e", "output volume of (get volume settings)"],
                    text=True, timeout=2
                ).strip()
                return int(out) if out.isdigit() else 50
            elif self.os_type == "linux":
                # 1. 优先尝试 wpctl (现代 Linux / Ubuntu / PipeWire 官方工具)
                try:
                    out = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], text=True, timeout=2).strip()
                    for token in out.split():
                        try:
                            val = float(token)
                            return int(round(val * 100))
                        except ValueError:
                            continue
                except Exception:
                    pass
                # 2. 尝试 pactl
                try:
                    out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], text=True, timeout=2)
                    for part in out.split("/"):
                        part = part.strip()
                        if part.endswith("%"):
                            return int(part[:-1])
                except Exception:
                    pass
                # 3. 尝试 amixer
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
                    return
                endpoint = self._get_win_com_endpoint()
                if endpoint:
                    endpoint.SetMasterVolumeLevelScalar(volume / 100.0, None)
                    return
            elif self.os_type == "macos":
                subprocess.run(["osascript", "-e", f"set volume output volume {volume}"], timeout=2)
            elif self.os_type == "linux":
                # 1. 优先尝试 wpctl (PipeWire / WirePlumber)
                try:
                    vol_float = volume / 100.0
                    res = subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{vol_float:.2f}"], timeout=2)
                    if res.returncode == 0:
                        return
                except Exception:
                    pass
                # 2. 尝试 pactl
                try:
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"], timeout=2)
                    return
                except Exception:
                    pass
                # 3. 尝试 amixer
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

def register_bluez_spp(channel=1):
    """在 Linux 上通过 BlueZ D-Bus 官方接口注册 SPP (Serial Port Profile) SDP 记录"""
    if platform.system() != "Linux":
        return
    try:
        import dbus
        import dbus.service
        from dbus.mainloop.glib import DBusGMainLoop
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object('org.bluez', '/org/bluez'), 'org.bluez.ProfileManager1')

        class BlueZProfile(dbus.service.Object):
            @dbus.service.method('org.bluez.Profile1', in_signature='', out_signature='')
            def Release(self):
                pass

        profile = BlueZProfile(bus, '/bluevolume/spp')
        opts = {
            'Name': 'BlueVolume Serial Port',
            'Channel': dbus.UInt16(channel),
        }
        manager.RegisterProfile('/bluevolume/spp', '00001101-0000-1000-8000-00805f9b34fb', opts)
        print(f'[Bluetooth] BlueZ D-Bus: SPP profile registered for channel {channel}')
    except Exception as e:
        # 如果已经注册或不可用，捕获不阻断
        print(f'[Bluetooth] BlueZ profile note: {e}')

def start_rfcomm_server(audio_ctrl: AudioController, preferred_channel=1):
    """启动经典蓝牙 RFCOMM 服务端 (跨平台支持: Linux BlueZ / Windows 11 AF_BLUETOOTH)"""
    server_sock = None
    actual_channel = preferred_channel
    # 优先尝试传入的通道，若被系统占用（如 Windows 常用通道 1-3 被内置协议保留），自动寻找可用通道 (1-30)
    candidate_channels = [preferred_channel] + [c for c in range(1, 31) if c != preferred_channel]

    for ch in candidate_channels:
        try:
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            sock.bind(("00:00:00:00:00:00", ch))
            sock.listen(1)
            server_sock = sock
            actual_channel = ch
            break
        except Exception:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    if not server_sock:
        print("[Bluetooth] RFCOMM initialization: No available RFCOMM channel could be bound.")
        return

    print(f"[Bluetooth] RFCOMM server listening on RFCOMM channel {actual_channel}...")
    register_bluez_spp(actual_channel)

    try:
        while True:
            client_sock, client_info = server_sock.accept()
            print(f"[Bluetooth] Accepted RFCOMM client: {client_info}")
            handler = ConnectionHandler(client_sock, client_info, audio_ctrl)
            threading.Thread(target=handler.handle, daemon=True).start()
    except Exception as e:
        print(f"[Bluetooth] RFCOMM server error: {e}")

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
