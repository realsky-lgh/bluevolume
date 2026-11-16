#!/usr/bin/env python3
"""
生成 BlueVolume 超清、极具科技与艺术设计感的 Android 应用图标
"""

import os
import math
from PIL import Image, ImageDraw, ImageFilter

def create_bluevolume_icon(size=512):
    # 创建超采样画布 (2x 超采样以达到完美的超平滑抗锯齿)
    w = size * 2
    h = size * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center_x = w / 2
    center_y = h / 2

    # 1. 绘制深邃背景底板 (深曜石蓝到暗夜星云渐变)
    # 底部渐变圆形/超椭圆 (Squircle)
    margin = w * 0.05
    for i in range(int(h)):
        ratio = i / h
        # 渐变从 #0A0F1D 到 #0D1B2A 再到 #080D1A
        r = int(10 + ratio * 8)
        g = int(18 + ratio * 15)
        b = int(36 + ratio * 30)
        draw.line([(0, i), (w, i)], fill=(r, g, b, 255))

    # 2. 绘制微妙的中心发光径向光晕 (Cyan Glow)
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    for radius in range(int(w * 0.42), 0, -6):
        alpha = int((1.0 - (radius / (w * 0.42))) ** 1.8 * 65)
        glow_draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            fill=(0, 242, 254, alpha)
        )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=18))
    img = Image.alpha_composite(img, glow_layer)
    draw = ImageDraw.Draw(img)

    # 3. 绘制外围科技刻度与音量同心声波环 (Concentric Ripple Waves)
    outer_rings = [
        (0.38, (0, 229, 255, 30), 4),
        (0.32, (56, 189, 248, 45), 5),
        (0.26, (14, 165, 233, 60), 6),
    ]
    for r_ratio, color, stroke_w in outer_rings:
        r = w * r_ratio
        # 绘制两侧扩散的音波弧度 (左侧 -135° ~ -45°, 右侧 45° ~ 135°)
        # 右侧声波弧
        draw.arc(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            start=-45, end=45, fill=color, width=stroke_w * 2
        )
        # 左侧声波弧
        draw.arc(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            start=135, end=225, fill=color, width=stroke_w * 2
        )

    # 4. 绘制中心主音量控制盘与发光胶囊环
    core_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    core_draw = ImageDraw.Draw(core_layer)

    # 主控圆盘阴影与发光外环
    core_r = w * 0.20
    # 外光环
    core_draw.ellipse(
        [center_x - core_r - 12, center_y - core_r - 12, center_x + core_r + 12, center_y + core_r + 12],
        fill=(14, 165, 233, 50)
    )
    # 暗色内衬圆盘
    core_draw.ellipse(
        [center_x - core_r, center_y - core_r, center_x + core_r, center_y + core_r],
        fill=(15, 23, 42, 240),
        outline=(56, 189, 248, 200),
        width=6
    )

    # 5. 绘制核心高级发光蓝牙标志 (Bluetooth Rune)
    # 精心校准的几何节点坐标
    bt_h = core_r * 1.25
    bt_w = bt_h * 0.58
    x_center = center_x
    y_center = center_y

    x_stem = x_center - bt_w * 0.12
    y_top = y_center - bt_h * 0.5
    y_bot = y_center + bt_h * 0.5
    y_mid = y_center
    x_right = x_stem + bt_w * 0.65
    y_upper_tip = y_center - bt_h * 0.25
    y_lower_tip = y_center + bt_h * 0.25
    x_left_diag = x_stem - bt_w * 0.42

    # 绘制蓝牙主体线条（发光底层 + 亮白顶层）
    points_path = [
        # 竖直中轴
        [(x_stem, y_top), (x_stem, y_bot)],
        # 上半部折线: 中轴下 -> 右上 -> 中轴中
        [(x_stem, y_lower_tip), (x_right, y_upper_tip), (x_stem, y_top)],
        # 下半部折线: 中轴上 -> 右下 -> 中轴底
        [(x_stem, y_upper_tip), (x_right, y_lower_tip), (x_stem, y_bot)],
        # 左下天线翅膀
        [(x_left_diag, y_lower_tip + (bt_h * 0.08)), (x_stem, y_mid)],
        # 左上天线翅膀
        [(x_left_diag, y_upper_tip - (bt_h * 0.08)), (x_stem, y_mid)]
    ]

    # 发光青蓝光晕
    for pt1, pt2, *rest in points_path:
        pts = [pt1, pt2] + rest
        core_draw.line(pts, fill=(0, 242, 254, 255), width=24, joint="round")
    
    # 纯白中心亮芯
    for pt1, pt2, *rest in points_path:
        pts = [pt1, pt2] + rest
        core_draw.line(pts, fill=(255, 255, 255, 255), width=12, joint="round")

    # 6. 顶部与底部极简音量与状态刻度指示
    # 顶部微型声波指示点
    for offset_angle in [-30, -15, 0, 15, 30]:
        rad = math.radians(offset_angle - 90)
        dot_r = w * 0.35
        dx = center_x + dot_r * math.cos(rad)
        dy = center_y + dot_r * math.sin(rad)
        dot_size = 8 if offset_angle == 0 else 6
        core_draw.ellipse(
            [dx - dot_size, dy - dot_size, dx + dot_size, dy + dot_size],
            fill=(0, 242, 254, 200)
        )

    # 底部微型电源光弧
    power_r = core_r + 26
    core_draw.arc(
        [center_x - power_r, center_y - power_r, center_x + power_r, center_y + power_r],
        start=75, end=105, fill=(56, 189, 248, 220), width=6
    )

    img = Image.alpha_composite(img, core_layer)

    # 高清平滑抗锯齿缩放
    final_icon = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_icon

def main():
    base_res = "/home/realsky/bluevolume/android/app/src/main/res"

    sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    print("🎨 正在生成 BlueVolume 设计级多分辨率应用图标...")
    master_icon = create_bluevolume_icon(512)
    master_icon.save("/home/realsky/bluevolume/icon_master.png")
    print("✅ 已生成 512x512 高清母图: icon_master.png")

    for folder, px in sizes.items():
        folder_path = os.path.join(base_res, folder)
        os.makedirs(folder_path, exist_ok=True)
        icon_resized = master_icon.resize((px, px), Image.Resampling.LANCZOS)
        icon_resized.save(os.path.join(folder_path, "ic_launcher.png"))
        icon_resized.save(os.path.join(folder_path, "ic_launcher_round.png"))
        print(f"  -> 生成 {folder}/ic_launcher.png ({px}x{px})")

if __name__ == "__main__":
    main()
