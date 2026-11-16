package com.example.bluevolume.ui

import android.bluetooth.BluetoothDevice
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.bluevolume.bluetooth.BluetoothService
import com.example.bluevolume.bluetooth.ConnectionStatus
import com.example.bluevolume.ui.theme.*

@Composable
fun MainScreen(
    bluetoothService: BluetoothService,
    onShutdownAndExit: () -> Unit,
    onRequestPermissions: () -> Unit
) {
    val connectionStatus by bluetoothService.connectionStatus.collectAsState()
    val computerInfo by bluetoothService.computerInfo.collectAsState()
    val volume by bluetoothService.currentVolume.collectAsState()
    val errorMessage by bluetoothService.errorMessage.collectAsState()

    var showDeviceDialog by remember { mutableStateOf(false) }
    var showShutdownConfirmDialog by remember { mutableStateOf(false) }
    var pairedDevices by remember { mutableStateOf<List<BluetoothDevice>>(emptyList()) }
    var isShuttingDown by remember { mutableStateOf(false) }

    fun refreshDevices() {
        pairedDevices = bluetoothService.getPairedDevices()
    }

    Scaffold(
        containerColor = BgDark,
        topBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 18.dp, start = 20.dp, end = 20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "BlueVolume",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                Text(
                    text = "电脑音量与电源蓝牙遥控器",
                    fontSize = 12.sp,
                    color = TextSecondary
                )
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 20.dp, vertical = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // 1. 顶部：连接状态与电脑操作系统识别展示区
            ConnectionStatusCard(
                status = connectionStatus,
                info = computerInfo,
                onConnectClick = {
                    onRequestPermissions()
                    refreshDevices()
                    showDeviceDialog = true
                },
                onDisconnectClick = {
                    bluetoothService.disconnect()
                }
            )

            // 错误消息提示条
            AnimatedVisibility(visible = errorMessage != null) {
                Surface(
                    color = DangerRed.copy(alpha = 0.15f),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp)
                ) {
                    Text(
                        text = errorMessage ?: "",
                        color = DangerRed,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(10.dp),
                        textAlign = TextAlign.Center
                    )
                }
            }

            // 2. 中间：垂直音量上下滑动滑块 (需求 2)
            Box(
                modifier = Modifier.weight(1f),
                contentAlignment = Alignment.Center
            ) {
                VerticalVolumeSlider(
                    volume = volume,
                    onVolumeChange = { newVol ->
                        bluetoothService.setVolume(newVol)
                    },
                    enabled = connectionStatus == ConnectionStatus.CONNECTED
                )
            }

            // 3. 底部：关机按钮 (需求 3 & 需求 4)
            ShutdownSection(
                enabled = connectionStatus == ConnectionStatus.CONNECTED && !isShuttingDown,
                isShuttingDown = isShuttingDown,
                onClick = {
                    showShutdownConfirmDialog = true
                }
            )
        }
    }

    // 设备选择对话框 (需求 1)
    if (showDeviceDialog) {
        DeviceSelectDialog(
            devices = pairedDevices,
            onSelectDevice = { device ->
                showDeviceDialog = false
                bluetoothService.connectBluetooth(device)
            },
            onConnectTcp = { ip, port ->
                showDeviceDialog = false
                bluetoothService.connectTcp(ip, port)
            },
            onRefresh = { refreshDevices() },
            onDismiss = { showDeviceDialog = false }
        )
    }

    // 关机二次确认弹窗 (需求 3 & 4)
    if (showShutdownConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showShutdownConfirmDialog = false },
            icon = {
                Icon(
                    imageVector = Icons.Rounded.PowerSettingsNew,
                    contentDescription = "Shutdown Alert",
                    tint = DangerRed,
                    modifier = Modifier.size(44.dp)
                )
            },
            title = {
                Text(
                    text = "确认关闭电脑？",
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
            },
            text = {
                val computerName = computerInfo?.hostname?.ifBlank { null }
                    ?: computerInfo?.deviceName
                    ?: "目标电脑"
                val osDesc = computerInfo?.osName ?: "未知系统"

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "您即将向电脑【$computerName ($osDesc)】发送远程系统关机指令。",
                        color = TextPrimary,
                        fontSize = 14.sp
                    )
                    Text(
                        text = "• 请确保电脑上未保存的工作已妥善存储。\n• 关机指令发出后，手机端本应用也将彻底退出。",
                        color = TextSecondary,
                        fontSize = 13.sp
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        showShutdownConfirmDialog = false
                        isShuttingDown = true
                        bluetoothService.sendShutdown {
                            // 关机后，自身彻底退出 (需求 4)
                            onShutdownAndExit()
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = DangerRed)
                ) {
                    Text("确定关机", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showShutdownConfirmDialog = false }) {
                    Text("取消", color = TextSecondary)
                }
            },
            containerColor = SurfaceDark,
            shape = RoundedCornerShape(20.dp)
        )
    }
}

/**
 * 满足需求1：展示连接状态并高亮显示判断出来的电脑操作系统 (Windows / macOS / Linux)
 */
@Composable
fun ConnectionStatusCard(
    status: ConnectionStatus,
    info: com.example.bluevolume.bluetooth.ComputerInfo?,
    onConnectClick: () -> Unit,
    onDisconnectClick: () -> Unit
) {
    val isConnected = status == ConnectionStatus.CONNECTED

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp)),
        color = SurfaceDark,
        tonalElevation = 4.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f)
            ) {
                // 操作系统专属图标或连接状态图标
                Box(
                    modifier = Modifier
                        .size(46.dp)
                        .clip(CircleShape)
                        .background(
                            when (info?.osType?.lowercase()) {
                                "windows" -> WindowsColor.copy(alpha = 0.2f)
                                "macos" -> AppleColor.copy(alpha = 0.2f)
                                "linux" -> LinuxColor.copy(alpha = 0.2f)
                                else -> SurfaceDarkElevated
                            }
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    when (info?.osType?.lowercase()) {
                        "windows" -> Icon(Icons.Rounded.DesktopWindows, contentDescription = "Windows", tint = WindowsColor)
                        "macos" -> Icon(Icons.Rounded.LaptopMac, contentDescription = "macOS", tint = AppleColor)
                        "linux" -> Icon(Icons.Rounded.Terminal, contentDescription = "Linux", tint = LinuxColor)
                        else -> Icon(
                            imageVector = if (isConnected) Icons.Rounded.BluetoothConnected else Icons.Rounded.BluetoothDisabled,
                            contentDescription = null,
                            tint = if (isConnected) PrimaryBlue else TextMuted
                        )
                    }
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column {
                    // 设备名称 / 操作系统名称
                    Text(
                        text = when {
                            isConnected -> info?.osName?.ifBlank { "已连接电脑" } ?: "已连接电脑"
                            status == ConnectionStatus.CONNECTING -> "正在建立连接..."
                            else -> "未连接电脑"
                        },
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )

                    // 副标题：系统类别识别结果
                    Text(
                        text = when {
                            isConnected -> "已识别系统: ${info?.osType?.uppercase() ?: "未知"} (${info?.hostname})"
                            status == ConnectionStatus.CONNECTING -> "正在握手并识别操作系统..."
                            else -> "请先点击右侧连接电脑"
                        },
                        fontSize = 12.sp,
                        color = when (info?.osType?.lowercase()) {
                            "windows" -> WindowsColor
                            "macos" -> AppleColor
                            "linux" -> LinuxColor
                            else -> TextSecondary
                        }
                    )
                }
            }

            // 连接/断开操作按钮
            if (isConnected) {
                IconButton(onClick = onDisconnectClick) {
                    Icon(
                        imageVector = Icons.Rounded.LinkOff,
                        contentDescription = "断开",
                        tint = TextSecondary
                    )
                }
            } else {
                Button(
                    onClick = onConnectClick,
                    colors = ButtonDefaults.buttonColors(containerColor = PrimaryBlue),
                    shape = RoundedCornerShape(12.dp),
                    contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp)
                ) {
                    Text("连接", color = Color.Black, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                }
            }
        }
    }
}

/**
 * 满足需求3：醒目的关机按钮
 */
@Composable
fun ShutdownSection(
    enabled: Boolean,
    isShuttingDown: Boolean,
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .clip(RoundedCornerShape(16.dp)),
        colors = ButtonDefaults.buttonColors(
            containerColor = DangerRed,
            disabledContainerColor = SurfaceDarkElevated
        )
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = Icons.Rounded.PowerSettingsNew,
                contentDescription = "关机",
                tint = if (enabled) Color.White else TextMuted,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = if (isShuttingDown) "关机中，应用即将退出..." else "电脑关机",
                color = if (enabled) Color.White else TextMuted,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}
