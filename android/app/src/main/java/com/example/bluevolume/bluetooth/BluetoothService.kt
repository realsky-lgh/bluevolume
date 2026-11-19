package com.example.bluevolume.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.util.Log
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.util.UUID

enum class ConnectionStatus {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    ERROR
}

data class ComputerInfo(
    val osType: String = "",       // "windows" | "macos" | "linux" | "unknown"
    val osName: String = "",       // e.g. "Windows 11", "Ubuntu 24.04 LTS"
    val hostname: String = "",     // e.g. "DESKTOP-ABC"
    val deviceName: String = ""    // 蓝牙或网络设备名
)

class BluetoothService(private val context: Context) {
    private val TAG = "BlueVolumeService"

    // 标准蓝牙 SPP (Serial Port Profile) UUID
    private val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

    private val bluetoothAdapter: BluetoothAdapter? = BluetoothAdapter.getDefaultAdapter()
    private val prefs = context.getSharedPreferences("bluevolume_prefs", Context.MODE_PRIVATE)

    private val _connectionStatus = MutableStateFlow(ConnectionStatus.DISCONNECTED)
    val connectionStatus: StateFlow<ConnectionStatus> = _connectionStatus.asStateFlow()

    private val _computerInfo = MutableStateFlow<ComputerInfo?>(null)
    val computerInfo: StateFlow<ComputerInfo?> = _computerInfo.asStateFlow()

    private val _currentVolume = MutableStateFlow(50)
    val currentVolume: StateFlow<Int> = _currentVolume.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private var btSocket: BluetoothSocket? = null
    private var tcpSocket: Socket? = null
    private var outputStream: OutputStream? = null
    private var reader: BufferedReader? = null

    // 音量调节防抖/节流
    private var volumeJob: Job? = null

    /**
     * 满足“打开后通过蓝牙自动连接电脑”：自动连接上次成功连接的电脑
     */
    @SuppressLint("MissingPermission")
    fun tryAutoConnect() {
        if (_connectionStatus.value == ConnectionStatus.CONNECTED || 
            _connectionStatus.value == ConnectionStatus.CONNECTING) return
        val lastMac = prefs.getString("last_device_mac", null)
        val paired = getPairedDevices()
        val target = if (lastMac != null) {
            paired.find { it.address.equals(lastMac, ignoreCase = true) }
        } else {
            paired.find { (it.name ?: "").contains("ubutu", ignoreCase = true) }
        }
        target?.let {
            Log.d(TAG, "Auto connecting to: ${it.name} [${it.address}]")
            connectBluetooth(it)
        }
    }

    /**
     * 获取系统已配对的蓝牙设备列表
     */
    @SuppressLint("MissingPermission")
    fun getPairedDevices(): List<BluetoothDevice> {
        return try {
            bluetoothAdapter?.bondedDevices?.toList() ?: emptyList()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get bonded devices", e)
            emptyList()
        }
    }

    /**
     * 通过蓝牙 SPP 连接指定的电脑设备 (支持多级降级防失败)
     */
    @SuppressLint("MissingPermission")
    fun connectBluetooth(device: BluetoothDevice) {
        disconnect()
        _connectionStatus.value = ConnectionStatus.CONNECTING
        _errorMessage.value = null

        serviceScope.launch {
            var socket: BluetoothSocket? = null
            try {
                Log.d(TAG, "Connecting to Bluetooth device: ${device.name} [${device.address}]")
                // 取消扫描以显著提升连接速度与稳定性
                bluetoothAdapter?.cancelDiscovery()

                // 尝试连接逻辑：先尝试标准 SPP，若报 read failed 则降级到反射 Channel 1
                socket = createAndConnectSocket(device)

                btSocket = socket
                outputStream = socket.outputStream
                reader = BufferedReader(InputStreamReader(socket.inputStream))

                _connectionStatus.value = ConnectionStatus.CONNECTED
                prefs.edit().putString("last_device_mac", device.address).apply()
                _computerInfo.value = ComputerInfo(
                    deviceName = device.name ?: device.address,
                    osType = "unknown",
                    osName = "正在识别系统...",
                    hostname = device.name ?: "Unknown"
                )

                // 请求系统信息
                sendRaw(Protocol.makeGetSystemInfo())

                // 启动读取循环
                startListenLoop()
            } catch (e: Exception) {
                Log.e(TAG, "Bluetooth connection failed", e)
                try {
                    socket?.close()
                } catch (_: Exception) {}
                _errorMessage.value = "蓝牙连接失败: ${e.localizedMessage ?: "握手超时"}"
                _connectionStatus.value = ConnectionStatus.ERROR
                disconnect()
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun createAndConnectSocket(device: BluetoothDevice): BluetoothSocket {
        // 方法 1：标准安全 SPP UUID
        try {
            Log.d(TAG, "[Strategy 1] Connecting with standard secure SPP UUID...")
            val s = device.createRfcommSocketToServiceRecord(SPP_UUID)
            s.connect()
            Log.d(TAG, "[Strategy 1] Connected successfully!")
            return s
        } catch (e1: Exception) {
            Log.w(TAG, "[Strategy 1] Failed (${e1.message}), trying Strategy 2 (Insecure)...")
        }

        // 方法 2：非安全 SPP UUID
        try {
            Log.d(TAG, "[Strategy 2] Connecting with insecure SPP UUID...")
            val s = device.createInsecureRfcommSocketToServiceRecord(SPP_UUID)
            s.connect()
            Log.d(TAG, "[Strategy 2] Connected successfully!")
            return s
        } catch (e2: Exception) {
            Log.w(TAG, "[Strategy 2] Failed (${e2.message}), trying Strategy 3 (Reflection Channel 1)...")
        }

        // 方法 3：通过反射依次尝试连接底层的 RFCOMM 通道 (优先 Channel 1，兼容 Windows 动态分配通道)
        val channelsToTry = listOf(1, 4, 2, 3, 5, 6, 7, 8)
        for (ch in channelsToTry) {
            var s: BluetoothSocket? = null
            try {
                Log.d(TAG, "[Strategy 3] Trying RFCOMM channel $ch via reflection...")
                val m = device.javaClass.getMethod("createRfcommSocket", Int::class.javaPrimitiveType)
                s = m.invoke(device, ch) as BluetoothSocket
                s.connect()
                Log.d(TAG, "[Strategy 3] Connected successfully via RFCOMM channel $ch!")
                return s
            } catch (e3: Exception) {
                try { s?.close() } catch (_: Exception) {}
                Log.w(TAG, "[Strategy 3] Channel $ch failed: ${e3.message}")
            }
        }

        // 方法 4：非安全反射依次尝试通道
        for (ch in channelsToTry) {
            var sFinal: BluetoothSocket? = null
            try {
                Log.d(TAG, "[Strategy 4] Trying insecure RFCOMM channel $ch via reflection...")
                val mInsecure = device.javaClass.getMethod("createInsecureRfcommSocket", Int::class.javaPrimitiveType)
                sFinal = mInsecure.invoke(device, ch) as BluetoothSocket
                sFinal.connect()
                Log.d(TAG, "[Strategy 4] Connected successfully via insecure RFCOMM channel $ch!")
                return sFinal
            } catch (e4: Exception) {
                try { sFinal?.close() } catch (_: Exception) {}
                Log.w(TAG, "[Strategy 4] Insecure channel $ch failed: ${e4.message}")
            }
        }

        throw Exception("所有蓝牙连接策略（SPP UUID / RFCOMM 1-8）均失败，请检查配对与服务端状态")
    }

    /**
     * 备用通道：通过 TCP 连接电脑 (WiFi/热点/蓝牙网络)
     */
    fun connectTcp(host: String, port: Int = 8888) {
        disconnect()
        _connectionStatus.value = ConnectionStatus.CONNECTING
        _errorMessage.value = null

        serviceScope.launch {
            try {
                Log.d(TAG, "Connecting to TCP server: $host:$port")
                val socket = Socket()
                socket.connect(InetSocketAddress(host, port), 5000)
                tcpSocket = socket
                outputStream = socket.getOutputStream()
                reader = BufferedReader(InputStreamReader(socket.getInputStream()))

                _connectionStatus.value = ConnectionStatus.CONNECTED
                _computerInfo.value = ComputerInfo(
                    deviceName = "$host:$port",
                    osType = "unknown",
                    osName = "正在识别系统...",
                    hostname = host
                )

                // 发送查询
                sendRaw(Protocol.makeGetSystemInfo())

                // 启动读取循环
                startListenLoop()
            } catch (e: Exception) {
                Log.e(TAG, "TCP connection failed", e)
                _errorMessage.value = "网络连接失败: ${e.localizedMessage ?: "请检查IP与端口"}"
                _connectionStatus.value = ConnectionStatus.ERROR
                disconnect()
            }
        }
    }

    private fun startListenLoop() {
        serviceScope.launch {
            try {
                val currentReader = reader ?: return@launch
                while (_connectionStatus.value == ConnectionStatus.CONNECTED) {
                    val line = currentReader.readLine() ?: break
                    if (line.isNotBlank()) {
                        handleIncomingMessage(line)
                    }
                }
            } catch (e: Exception) {
                Log.d(TAG, "Listen loop ended: ${e.message}")
            } finally {
                if (_connectionStatus.value == ConnectionStatus.CONNECTED) {
                    _connectionStatus.value = ConnectionStatus.DISCONNECTED
                }
            }
        }
    }

    private fun handleIncomingMessage(rawJson: String) {
        val msg = Protocol.parse(rawJson) ?: return
        Log.d(TAG, "Received protocol message: $msg")

        when (msg.type.uppercase()) {
            "SYSTEM_INFO" -> {
                _computerInfo.value = _computerInfo.value?.copy(
                    osType = msg.os_type ?: "unknown",
                    osName = msg.os_name ?: "Unknown OS",
                    hostname = msg.hostname ?: ""
                )
                msg.volume?.let {
                    _currentVolume.value = it
                }
            }
            "VOLUME_CHANGED" -> {
                msg.volume?.let {
                    _currentVolume.value = it
                }
            }
            "SHUTDOWN_ACK" -> {
                Log.d(TAG, "Shutdown ACK received, computer is powering down.")
            }
        }
    }

    /**
     * 设置电脑播放设备音量大小 (带节流防抖)
     */
    fun setVolume(volume: Int) {
        _currentVolume.value = volume
        volumeJob?.cancel()
        volumeJob = serviceScope.launch {
            delay(30) // 30ms 节流，避免高频滑动阻塞蓝牙通信管道
            sendRaw(Protocol.makeSetVolume(volume))
        }
    }

    /**
     * 发送关机命令给电脑
     */
    fun sendShutdown(onSuccess: () -> Unit) {
        serviceScope.launch {
            try {
                sendRaw(Protocol.makeShutdown())
                delay(400) // 确保数据包冲刷出缓冲区
                withContext(Dispatchers.Main) {
                    onSuccess()
                }
            } catch (e: Exception) {
                Log.e(TAG, "Send shutdown failed", e)
            }
        }
    }

    private fun sendRaw(data: String) {
        try {
            outputStream?.let {
                it.write(data.toByteArray(Charsets.UTF_8))
                it.flush()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Send raw data failed", e)
        }
    }

    /**
     * 断开连接并释放资源
     */
    fun disconnect() {
        try {
            outputStream?.close()
            reader?.close()
            btSocket?.close()
            tcpSocket?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error closing sockets", e)
        } finally {
            outputStream = null
            reader = null
            btSocket = null
            tcpSocket = null
            _connectionStatus.value = ConnectionStatus.DISCONNECTED
        }
    }

    fun release() {
        disconnect()
        serviceScope.cancel()
    }
}
