package com.example.bluevolume

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import com.example.bluevolume.bluetooth.BluetoothService
import com.example.bluevolume.ui.MainScreen
import com.example.bluevolume.ui.theme.BlueVolumeTheme
import kotlin.system.exitProcess

class MainActivity : ComponentActivity() {

    private lateinit var bluetoothService: BluetoothService

    // 动态权限请求器
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            bluetoothService.tryAutoConnect()
        } else {
            Toast.makeText(this, "需要蓝牙权限才能搜索和连接电脑", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bluetoothService = BluetoothService(applicationContext)

        checkAndRequestPermissions()

        setContent {
            BlueVolumeTheme {
                MainScreen(
                    bluetoothService = bluetoothService,
                    onShutdownAndExit = {
                        // 满足需求4：关机后，自身也彻底退出
                        handleShutdownAndExit()
                    },
                    onRequestPermissions = {
                        checkAndRequestPermissions()
                    }
                )
            }
        }
    }

    private fun checkAndRequestPermissions() {
        val permissionsToRequest = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED
            ) {
                permissionsToRequest.add(Manifest.permission.BLUETOOTH_CONNECT)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN)
                != PackageManager.PERMISSION_GRANTED
            ) {
                permissionsToRequest.add(Manifest.permission.BLUETOOTH_SCAN)
            }
        } else {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED
            ) {
                permissionsToRequest.add(Manifest.permission.ACCESS_FINE_LOCATION)
            }
        }

        if (permissionsToRequest.isNotEmpty()) {
            permissionLauncher.launch(permissionsToRequest.toTypedArray())
        } else {
            bluetoothService.tryAutoConnect()
        }
    }

    /**
     * 满足需求4：彻底退出自身应用
     */
    private fun handleShutdownAndExit() {
        runOnUiThread {
            Toast.makeText(this, "关机指令已送达电脑，应用已退出", Toast.LENGTH_LONG).show()
        }

        // 释放蓝牙与线程资源
        bluetoothService.release()

        // 结束所有 Activity 并彻底终结本进程
        finishAffinity()
        android.os.Process.killProcess(android.os.Process.myPid())
        exitProcess(0)
    }

    
    override fun onResume() {
        super.onResume()
        bluetoothService.tryAutoConnect()
    }

    override fun onDestroy() {
        super.onDestroy()
        bluetoothService.release()
    }
}
