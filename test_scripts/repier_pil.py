#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：repier_pil.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/14 08:45 
@Describe: 
"""
import os
from PIL import Image,ImageEnhance


def repair_png_batch(input_dir, output_dir):
    """
    批量修复一个文件夹中的所有 PNG 文件。

    参数:
        input_dir (str): 输入文件夹路径（包含损坏的 PNG 文件）
        output_dir (str): 输出文件夹路径（保存修复后的 PNG 文件）
    """
    # 确保输出文件夹存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 遍历输入文件夹中的所有文件
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".png"):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            # adjust_brightness(input_path, output_path, brightness_factor)

            print(f"正在修复: {input_path} -> {output_path}")
            try:
                img = Image.open(input_path)
                img.save(output_path, format="PNG")
                print(f"修复成功: {output_path}")
                # enhance_image(output_path, output_path, brightness_factor)
            except Exception as e:
                print(f"修复失败: {input_path}, 错误: {e}")


def enhance_image(input_path, output_path, brightness_factor=1.2, contrast_factor=1.1, saturation_factor=1.1):
    """
    调整图像的亮度、对比度和饱和度。

    参数:
        input_path (str): 输入文件路径
        output_path (str): 输出文件路径
        brightness_factor (float): 亮度调整因子（默认 1.2 表示增加 20% 亮度）
        contrast_factor (float): 对比度调整因子（默认 1.1 表示增加 10% 对比度）
        saturation_factor (float): 饱和度调整因子（默认 1.1 表示增加 10% 饱和度）
    """
    try:
        # 打开图片
        img = Image.open(input_path)

        # 调整亮度
        print(f"调整亮度，因子: {brightness_factor}")
        enhancer_brightness = ImageEnhance.Brightness(img)
        bright_img = enhancer_brightness.enhance(brightness_factor)

        # 调整对比度
        print(f"调整对比度，因子: {contrast_factor}")
        enhancer_contrast = ImageEnhance.Contrast(bright_img)
        contrast_img = enhancer_contrast.enhance(contrast_factor)

        # 调整饱和度
        print(f"调整饱和度，因子: {saturation_factor}")
        enhancer_saturation = ImageEnhance.Color(contrast_img)
        final_img = enhancer_saturation.enhance(saturation_factor)

        # 保存调整后的图片
        final_img.save(output_path, format="PNG")
        print(f"亮度、对比度和饱和度调整完成，保存至: {output_path}")
    except Exception as e:
        print(f"调整失败: {e}")

# 示例用法
if __name__ == "__main__":
    input_folder = "E:/Project Code/Python Code/a_pygame/三界奇谈/Graphics/Maps/1514/mask"  # 替换为你的损坏文件文件夹
    output_folder = r"D:\Windows\Desktop\待删除\修复"  # 替换为修复后文件保存文件夹
    brightness_factor = 1.2  # 调整亮度因子，例如 1.2 表示增加 20% 亮度
    repair_png_batch(input_folder, output_folder)