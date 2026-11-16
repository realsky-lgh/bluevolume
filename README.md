# BlueVolume - 电脑音量与电源蓝牙遥控器 (Android + PC)

一款现代、优雅的 Android 蓝牙遥控应用与跨平台电脑端伴侣程序，满足以下核心需求：
1. **蓝牙连接电脑，判断电脑操作系统**（精准识别 Windows / macOS / Linux 并展示系统专属图标与主机名）。
2. **上下滑动垂直胶囊滑块调节电脑当前播放设备音量**（支持实时绝对音量同步、拖拽阻尼与 30ms 节流防抖）。
3. **醒目关机按钮与二次安全确认**（防误触 Material 3 确认对话框）。
4. **执行关机后，应用自身彻底退出**（自动释放资源，关闭所有 Activity 并终结自身进程）。

---

## 目录结构

```text
bluevolume/
├── android/                         # Android 端完整工程 (Android Studio 开箱即用)
│   ├── app/
│   │   ├── build.gradle.kts
│   │   ├── src/main/
│   │   │   ├── AndroidManifest.xml
│   │   │   └── java/com/example/bluevolume/
│   │   │       ├── MainActivity.kt               # 权限申请、生命周期与彻底退出
│   │   │       ├── bluetooth/
│   │   │       │   ├── BluetoothService.kt       # 蓝牙 SPP / TCP 通信服务
│   │   │       │   └── Protocol.kt               # 双向 JSON 通信协议
│   │   │       └── ui/
│   │   │           ├── MainScreen.kt             # 主界面、系统识别徽标、关机确认弹窗
│   │   │           ├── VerticalVolumeSlider.kt   # 上下滑动垂直音量滑块
│   │   │           ├── DeviceSelectDialog.kt     # 电脑选择对话框 (蓝牙/局域网双模)
│   │   │           └── theme/                    # 现代暗黑科技风设计主题
│   │   └── proguard-rules.pro
│   ├── build.gradle.kts
│   └── settings.gradle.kts
├── server/                          # 电脑端跨平台伴侣程序 (PC Companion Server)
│   ├── pc_server.py                 # 支持 Windows / macOS / Linux 音量控制与关机
│   └── requirements.txt             # 依赖说明
├── tests/                           # 协议与底层音频调节集成测试
│   └── test_server_protocol.py
└── README.md
```

---

## 核心功能实现原理

### 1. 为什么需要 PC 端伴侣脚本？
- **标准蓝牙 HID 的局限**：如果仅使用纯蓝牙 HID（模拟键盘/鼠标/多媒体键盘），手机只能单向盲发 `Volume Up` / `Volume Down` 脉冲，**无法获取电脑当前实际音量百分比**，也**无法判断电脑是 Windows 还是 macOS 还是 Linux**，更无法跨平台可靠触发系统深度关机。
- **BlueVolume 的解决方案**：电脑端运行仅数百行代码的超轻量跨平台脚本（`pc_server.py`），通过 **经典蓝牙 RFCOMM (SPP)** 或 **本地网络 Socket** 建立全双工通信：
  - 连接建立时，电脑自动上报 OS 类型（`windows` / `macos` / `linux`）、发行版名称、主机名以及当前默认扬声器的实际音量。
  - 手机主界面根据上报结果动态展示系统徽章（Windows 微软徽章 / macOS 苹果徽章 / Linux 企鹅终端徽章）。

### 2. 垂直上下滑动音量条 (`VerticalVolumeSlider.kt`)
- 仿控制中心胶囊风格：触摸滑块上下拖拽或点击，高度实时动态升降。
- 采用 30ms 协程节流（Debounce/Throttle），避免用户在手指快速上下滑动时瞬间堆积数百条蓝牙通信数据包。
- 跨平台原生音量控制：
  - **Windows**：调用 Windows Core Audio API（`IAudioEndpointVolume`）或 PowerShell。
  - **macOS**：原生执行 AppleScript (`osascript`) 设置系统音量。
  - **Linux**：原生支持 `pactl` (PulseAudio / PipeWire) 和 `amixer` (ALSA)。

### 3. 关机按钮与二次确认 (`MainScreen.kt`)
- 点击底部的危险操作关机按钮，弹出 Material 3 确认对话框。
- 明确提示电脑名称与系统信息，提示用户未保存的工作需要先保存。

### 4. 关机后自身彻底退出 (`MainActivity.kt`)
- 确认关机后，Android 端向电脑发出 `{"type": "SHUTDOWN"}` 指令。
- 电脑端接收指令后回传 `SHUTDOWN_ACK`，并在 1 秒后执行系统安全关机。
- Android 端在确认指令发送后：
  1. 调用 `BluetoothService.release()` 关闭 Socket 并注销后台协程。
  2. 调用 `finishAffinity()` 销毁所有任务栈。
  3. 执行 `android.os.Process.killProcess(android.os.Process.myPid())` 与 `exitProcess(0)` 彻底销毁进程退出，不留后台常驻。

---

## 快速使用指南

### 第一步：启动电脑端伴侣服务端（可配置开机自启）

#### 选项 A：开机自启动守护（推荐）
- **Linux (Ubuntu / Debian 等)**：
  ```bash
  ./server/autostart_linux.sh install
  ```
  *(注：已为当前主机完成配置并启用了 `systemd --user` 与 linger 守护，开机无需手动干预自动常驻)*

- **Windows**：
  双击运行 `server\autostart_windows.bat`（将自动生成无黑框后台静默运行项至 Windows Startup 启动目录）。

- **macOS**：
  ```bash
  ./server/autostart_macos.sh install
  ```

#### 选项 B：手动前台运行测试
```bash
cd server
python3 pc_server.py
```

终端将打印：
```text
============================================================
 BlueVolume PC Companion Agent 
============================================================
 Detected OS    : Ubuntu 24.04 LTS (linux)
 Hostname       : my-desktop
 Current Volume : 42%
============================================================
[TCP] Server listening on 0.0.0.0:8888 (WiFi / 蓝牙网络互联)
[Bluetooth] RFCOMM server listening on RFCOMM channel 1...
[Ready] Waiting for connection from Android App...
```

### 第二步：Android 客户端编译与安装
1. 使用 **Android Studio** 打开 `bluevolume/android` 目录。
2. 连接 Android 手机或模拟器，点击 **Run** 即可编译并安装到手机。
3. 首次启动时，App 会自动申请蓝牙连接与扫描权限。

### 第三步：操作流程
1. **配对与连接**：
   - 方式 A（蓝牙直连）：在手机系统“设置 -> 蓝牙”中与电脑完成配对，进入 App 点击顶部“连接”，在列表中选择已配对电脑即可。
   - 方式 B（局域网/WiFi/热点备用）：点击对话框底部的“切换至局域网模式”，输入电脑 IP（端口默认 8888）即可直连。
2. **操作系统识别**：
   - 成功连接后，顶部卡片立即显示：
     - Windows 电脑：显示蓝色 Windows 徽章及 Windows 10/11 系统名。
     - macOS 电脑：显示银灰色 macOS 徽章及系统版本。
     - Linux 电脑：显示明黄色 Linux 徽章及发行版全称（如 Ubuntu 24.04 LTS）。
3. **音量调节**：
   - 上下滑动中央的胶囊滑块，电脑播放设备的音量将实时毫秒级响应。
4. **电脑关机与自身退出**：
   - 点击底部红色“电脑关机”按钮，弹出二次确认对话框。
   - 点击“确定关机”，电脑将执行关机，手机端弹出提示并彻底退出自身进程。
