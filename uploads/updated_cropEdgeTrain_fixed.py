
import os
import cv2
import torch
import shutil
import numpy as np
from ultralytics import YOLO

def slice_image_based_on_labels(image_path, label_path, output_img_dir, output_lbl_dir, slice_size=640, overlap_ratio=0.2):
    """
    根據標記框動態切割圖片，避免標記框被切斷，並確保覆蓋整個圖片。
    如果切片沒有任何標註，則不保存該切片。
    """
    # 讀取圖片
    img = cv2.imread(image_path)
    if img is None:
        print(f"無法讀取圖片 {image_path}")
        return

    height, width, _ = img.shape

    # 讀取標註文件（YOLO格式）
    labels = []
    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            labels = f.readlines()

    # 創建輸出目錄
    if not os.path.exists(output_img_dir):
        os.makedirs(output_img_dir)
    if not os.path.exists(output_lbl_dir):
        os.makedirs(output_lbl_dir)

    # 根據標記框動態調整切割區域
    for i in range(0, height, slice_size):
        for j in range(0, width, slice_size):
            x_min = j
            y_min = i
            x_max = min(j + slice_size, width)
            y_max = min(i + slice_size, height)

            # 初始化一個列表來存儲當前切片的標註
            slice_labels = []

            # 檢查每個標註框是否在當前切片內或跨越切片邊界
            for label in labels:
                cls, x_center, y_center, box_width, box_height = map(float, label.strip().split())
                x_center_abs = x_center * width
                y_center_abs = y_center * height
                box_width_abs = box_width * width
                box_height_abs = box_height * height

                box_xmin = x_center_abs - box_width_abs / 2
                box_ymin = y_center_abs - box_height_abs / 2
                box_xmax = x_center_abs + box_width_abs / 2
                box_ymax = y_center_abs + box_height_abs / 2

                # 如果標記框跨越了切片邊界，動態調整切片的邊界
                if box_xmin < x_max and box_xmax > x_min and box_ymin < y_max and box_ymax > y_min:
                    # 動態調整，使整個標記框位於一個patch內
                    new_x_center = (x_center_abs - x_min) / (x_max - x_min)
                    new_y_center = (y_center_abs - y_min) / (y_max - y_min)
                    new_box_width = box_width_abs / (x_max - x_min)
                    new_box_height = box_height_abs / (y_max - y_min)

                    # 確保標註框在 [0,1] 範圍內，並保存標註
                    if 0 <= new_x_center <= 1 and 0 <= new_y_center <= 1 and 0 <= new_box_width <= 1 and 0 <= new_box_height <= 1:
                        slice_labels.append(f"{cls} {new_x_center} {new_y_center} {new_box_width} {new_box_height}
")

            # 如果有標註框則保存切片
            if slice_labels:
                slice_img_name = f"{os.path.splitext(os.path.basename(image_path))[0]}_{i}_{j}.jpg"
                slice_img_path = os.path.join(output_img_dir, slice_img_name)
                cv2.imwrite(slice_img_path, img[y_min:y_max, x_min:x_max])

                # 保存切片標註
                slice_lbl_name = f"{os.path.splitext(os.path.basename(image_path))[0]}_{i}_{j}.txt"
                slice_lbl_path = os.path.join(output_lbl_dir, slice_lbl_name)
                with open(slice_lbl_path, 'w') as lbl_file:
                    lbl_file.writelines(slice_labels)

def prepare_dataset_based_on_labels(input_img_dir, input_lbl_dir, output_dir, slice_size=640, overlap_ratio=0.2):
    output_img_dir = os.path.join(output_dir, 'images')
    output_lbl_dir = os.path.join(output_dir, 'labels')

    # 清空輸出目錄
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_img_dir)
    os.makedirs(output_lbl_dir)

    # 遍歷所有圖片和標籤
    for img_file in os.listdir(input_img_dir):
        if img_file.endswith(('.jpg', '.png', '.jpeg')):
            image_path = os.path.join(input_img_dir, img_file)
            label_path = os.path.join(input_lbl_dir, f"{os.path.splitext(img_file)[0]}.txt")
            slice_image_based_on_labels(image_path, label_path, output_img_dir, output_lbl_dir, slice_size, overlap_ratio)

# Prepare both train and validation sets
def main_based_on_labels():
    # 配置路徑，請替換為你自己的路徑
    input_train_img_dir = 'D:/Github/PatchPicture/train/images'  # 原始訓練圖片路徑
    input_train_lbl_dir = 'D:/Github/PatchPicture/train/labels'  # 原始訓練標註路徑
    output_train_dir = 'D:/Github/PatchPicture/sliced/train'  # 切割後的訓練資料存放目錄

    input_val_img_dir = 'D:/Github/PatchPicture/valid/images'  # 原始驗證圖片路徑
    input_val_lbl_dir = 'D:/Github/PatchPicture/valid/labels'  # 原始驗證標註路徑
    output_val_dir = 'D:/Github/PatchPicture/sliced/valid'  # 切割後的驗證資料存放目錄

    # 準備訓練集，並根據標記框動態調整patch分佈
    print("正在準備訓練集，根據標記框調整patch分佈...")
    prepare_dataset_based_on_labels(input_train_img_dir, input_train_lbl_dir, output_train_dir, slice_size=640, overlap_ratio=0.2)

    print("正在準備驗證集，根據標記框調整patch分佈...")
    prepare_dataset_based_on_labels(input_val_img_dir, input_val_lbl_dir, output_val_dir, slice_size=640, overlap_ratio=0.2)

if __name__ == '__main__':
    main_based_on_labels()
