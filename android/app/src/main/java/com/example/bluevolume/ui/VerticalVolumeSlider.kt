package com.example.bluevolume.ui

import android.view.HapticFeedbackConstants
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.VolumeDown
import androidx.compose.material.icons.rounded.VolumeMute
import androidx.compose.material.icons.rounded.VolumeOff
import androidx.compose.material.icons.rounded.VolumeUp
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.bluevolume.ui.theme.*

/**
 * 满足需求2：上下滑动的垂直音量胶囊滑块
 * 支持触摸点击、上下连续拖拽、实时高度填充、触觉震动与平滑动画。
 */
@Composable
fun VerticalVolumeSlider(
    volume: Int,
    onVolumeChange: (Int) -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true
) {
    val view = LocalView.current
    var sliderSize by remember { mutableStateOf(IntSize.Zero) }

    // 平滑动画过度
    val animatedProgress by animateFloatAsState(
        targetValue = (volume.coerceIn(0, 100)) / 100f,
        label = "VolumeProgress"
    )

    // 音量图标动态选择
    val volumeIcon = when {
        volume == 0 -> Icons.Rounded.VolumeOff
        volume < 30 -> Icons.Rounded.VolumeMute
        volume < 70 -> Icons.Rounded.VolumeDown
        else -> Icons.Rounded.VolumeUp
    }

    Box(
        modifier = modifier
            .width(130.dp)
            .fillMaxHeight(0.65f)
            .shadow(24.dp, RoundedCornerShape(48.dp), spotColor = PrimaryBlue.copy(alpha = 0.25f))
            .clip(RoundedCornerShape(48.dp))
            .background(SurfaceDark)
            .onSizeChanged { sliderSize = it }
            .pointerInput(enabled) {
                if (!enabled) return@pointerInput

                // 点击跳转定位
                detectTapGestures { offset ->
                    if (sliderSize.height > 0) {
                        val touchRatio = 1f - (offset.y / sliderSize.height)
                        val targetVol = (touchRatio * 100).toInt().coerceIn(0, 100)
                        view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                        onVolumeChange(targetVol)
                    }
                }
            }
            .pointerInput(enabled) {
                if (!enabled) return@pointerInput

                // 拖动手势监听 (上下滑动)
                detectDragGestures(
                    onDragStart = {
                        view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                    },
                    onDrag = { change, _ ->
                        change.consume()
                        if (sliderSize.height > 0) {
                            val touchRatio = 1f - (change.position.y / sliderSize.height)
                            val targetVol = (touchRatio * 100).toInt().coerceIn(0, 100)
                            if (targetVol != volume) {
                                onVolumeChange(targetVol)
                            }
                        }
                    }
                )
            },
        contentAlignment = Alignment.BottomCenter
    ) {
        // 底部填充条 (随音量上下升高)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(animatedProgress)
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            AccentCyan,
                            PrimaryBlue
                        )
                    )
                )
        )

        // 内部浮层：顶部百分比与底部图标
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(vertical = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // 当前音量数值
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "$volume",
                    color = if (animatedProgress > 0.85f) Color(0xFF0F172A) else TextPrimary,
                    fontSize = 38.sp,
                    fontWeight = FontWeight.ExtraBold
                )
                Text(
                    text = "%",
                    color = if (animatedProgress > 0.85f) Color(0xFF1E293B) else TextSecondary,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }

            // 音量状态图标与提示
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Icon(
                    imageVector = volumeIcon,
                    contentDescription = "Volume Icon",
                    tint = if (animatedProgress > 0.18f) Color(0xFF0F172A) else TextPrimary,
                    modifier = Modifier.size(36.dp)
                )
                Text(
                    text = if (enabled) "上下滑动调节" else "未连接电脑",
                    color = if (animatedProgress > 0.18f) Color(0xFF1E293B) else TextMuted,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}
