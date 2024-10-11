import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageTk
import os

# 全域變數
rectangles = []
undo_stack = []
start_x, start_y = -1, -1
drawing = False
moving = False
resizing = False
selecting_area = False
img = None
img_tk = None
canvas = None
rect = None
selected_rect = None
selected_rect_index = None
hovered_rect = None
handle_size = 6
handles = {}
current_handle = None
selection_rect = None
root = None
scale_ratio = 1
zoom_level = 1.0
default_image_path = 'GUI.jpg'
default_image_height = 400
img_width = 0
img_height = 0

def load_image(filepath):
    global img, img_width, img_height
    if not os.path.exists(filepath):
        messagebox.showerror("錯誤", "圖片檔案不存在")
        return
    img = cv2.imread(filepath)
    if img is None:
        messagebox.showerror("錯誤", "無法讀取圖片檔案")
        return
    img_height, img_width = img.shape[:2]

def display_image():
    global img_tk, canvas, scale_ratio, selected_rect
    if img is None:
        return
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    if canvas_width <= 1 or canvas_height <= 1:
        root.after(100, display_image)
        return
    img_ratio = img_width / img_height
    canvas_ratio = canvas_width / canvas_height
    if img_ratio > canvas_ratio:
        base_scale = canvas_width / img_width
    else:
        base_scale = canvas_height / img_height
    scale_ratio = base_scale * zoom_level
    new_width = int(img_width * scale_ratio)
    new_height = int(img_height * scale_ratio)
    img_resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)
    img_tk = ImageTk.PhotoImage(img_pil)
    canvas.delete("all")
    canvas.config(scrollregion=(0, 0, new_width, new_height))
    canvas.create_image(0, 0, anchor='nw', image=img_tk)
    # 重新繪製所有矩形框
    for idx, rect_info in enumerate(rectangles):
        x1, y1, x2, y2 = rect_info['original_coords']
        x1_display = x1 * scale_ratio
        y1_display = y1 * scale_ratio
        x2_display = x2 * scale_ratio
        y2_display = y2 * scale_ratio
        rect_id = canvas.create_rectangle(x1_display, y1_display, x2_display, y2_display, outline='green', tags='rectangle')
        rectangles[idx]['id'] = rect_id  # 更新ID
        rectangles[idx]['coords'] = (x1_display, y1_display, x2_display, y2_display)  # 更新座標
        rectangles[idx]['hovered'] = False
    if selected_rect is not None and selected_rect_index is not None:
        # 更新選中矩形框的ID
        selected_rect = rectangles[selected_rect_index]['id']
        x1, y1, x2, y2 = rectangles[selected_rect_index]['coords']
        canvas.itemconfig(selected_rect, outline='red')
        draw_handles(x1, y1, x2, y2)

def on_window_resize(event):
    display_image()

def select_image():
    filepath = filedialog.askopenfilename(title="選擇圖片", filetypes=[("圖片檔案", "*.jpg;*.jpeg;*.png")])
    if filepath:
        load_image(filepath)
        global rectangles, selected_rect, selected_rect_index, handles
        rectangles.clear()
        selected_rect = None
        selected_rect_index = None
        handles.clear()
        display_image()

def draw_handles(x1, y1, x2, y2):
    global handles
    handle_positions = [
        (x1, y1),
        ((x1 + x2) / 2, y1),
        (x2, y1),
        (x2, (y1 + y2) / 2),
        (x2, y2),
        ((x1 + x2) / 2, y2),
        (x1, y2),
        (x1, (y1 + y2) / 2),
    ]
    if handles:
        for idx, (x, y) in enumerate(handle_positions):
            handle_id = handles.get(f"handle{idx}")
            if handle_id:
                canvas.coords(handle_id, x - handle_size, y - handle_size, x + handle_size, y + handle_size)
    else:
        for idx, (x, y) in enumerate(handle_positions):
            handle_id = canvas.create_rectangle(
                x - handle_size, y - handle_size, x + handle_size, y + handle_size,
                fill='blue', tags=("handle", f"handle{idx}")
            )
            handles[f"handle{idx}"] = handle_id

def check_handle_click(x, y):
    overlapping = canvas.find_overlapping(x, y, x, y)
    for item in overlapping:
        tags = canvas.gettags(item)
        if "handle" in tags:
            return item
    return None

def is_point_in_rect(x, y, rect_coords):
    x1, y1, x2, y2 = rect_coords
    return x1 <= x <= x2 and y1 <= y <= y2

def on_mouse_down(event):
    global start_x, start_y, rect, drawing, selected_rect, selected_rect_index, moving, resizing, current_handle, selecting_area, selection_rect
    x = canvas.canvasx(event.x)
    y = canvas.canvasy(event.y)
    if event.state & 0x0001:
        selecting_area = True
        start_x, start_y = x, y
        selection_rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='blue', dash=(4, 2))
        return
    handle = check_handle_click(x, y)
    if handle:
        current_handle = handle
        resizing = True
        undo_stack.append(('resize_start', selected_rect_index, rectangles[selected_rect_index]['coords']))
        return
    clicked_on_rect = False
    for idx, rect_info in enumerate(rectangles):
        x1, y1, x2, y2 = rect_info['coords']
        if is_point_in_rect(x, y, (x1, y1, x2, y2)):
            if selected_rect is not None and selected_rect != rect_info['id']:
                canvas.itemconfig(selected_rect, outline='green')
                for handle_id in handles.values():
                    canvas.delete(handle_id)
                handles.clear()
            selected_rect = rect_info['id']
            selected_rect_index = idx
            canvas.tag_raise(selected_rect)
            canvas.itemconfig(selected_rect, outline='red')
            draw_handles(x1, y1, x2, y2)
            clicked_on_rect = True
            moving = True
            start_x, start_y = x, y
            undo_stack.append(('move_start', selected_rect_index, (x1, y1, x2, y2)))
            break
    if not clicked_on_rect:
        if selected_rect is not None:
            canvas.itemconfig(selected_rect, outline='green')
            selected_rect = None
            selected_rect_index = None
            for handle_id in handles.values():
                canvas.delete(handle_id)
            handles.clear()
        start_x, start_y = x, y
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='green', tags='rectangle')
        drawing = True

def on_mouse_move(event):
    x = canvas.canvasx(event.x)
    y = canvas.canvasy(event.y)
    global rect, moving, start_x, start_y, resizing, current_handle, selecting_area, selection_rect, hovered_rect
    if drawing and rect:
        canvas.coords(rect, start_x, start_y, x, y)
    elif moving and selected_rect is not None:
        dx = x - start_x
        dy = y - start_y
        canvas.move(selected_rect, dx, dy)
        for handle_id in handles.values():
            canvas.move(handle_id, dx, dy)
        x1, y1, x2, y2 = canvas.coords(selected_rect)
        rectangles[selected_rect_index]['coords'] = (x1, y1, x2, y2)
        start_x, start_y = x, y
    elif resizing and current_handle and selected_rect is not None:
        handle_tags = canvas.gettags(current_handle)
        x1, y1, x2, y2 = rectangles[selected_rect_index]['coords']
        if "handle0" in handle_tags:
            x1, y1 = x, y
        elif "handle1" in handle_tags:
            y1 = y
        elif "handle2" in handle_tags:
            x2, y1 = x, y
        elif "handle3" in handle_tags:
            x2 = x
        elif "handle4" in handle_tags:
            x2, y2 = x, y
        elif "handle5" in handle_tags:
            y2 = y
        elif "handle6" in handle_tags:
            x1, y2 = x, y
        elif "handle7" in handle_tags:
            x1 = x
        canvas.coords(selected_rect, x1, y1, x2, y2)
        rectangles[selected_rect_index]['coords'] = (x1, y1, x2, y2)
        draw_handles(x1, y1, x2, y2)
    elif selecting_area and selection_rect:
        canvas.coords(selection_rect, start_x, start_y, x, y)
    else:
        is_over_rect = False
        for idx, rect_info in enumerate(rectangles):
            x1, y1, x2, y2 = rect_info['coords']
            if is_point_in_rect(x, y, (x1, y1, x2, y2)):
                if not rect_info['hovered']:
                    if hovered_rect is not None and hovered_rect != rect_info['id']:
                        canvas.itemconfig(hovered_rect, outline='green')
                        rect_idx = next((i for i, r in enumerate(rectangles) if r['id'] == hovered_rect), None)
                        if rect_idx is not None:
                            rectangles[rect_idx]['hovered'] = False
                    canvas.itemconfig(rect_info['id'], outline='blue')
                    rect_info['hovered'] = True
                    hovered_rect = rect_info['id']
                is_over_rect = True
                break
        if not is_over_rect:
            if hovered_rect is not None:
                canvas.itemconfig(hovered_rect, outline='green')
                rect_idx = next((i for i, r in enumerate(rectangles) if r['id'] == hovered_rect), None)
                if rect_idx is not None:
                    rectangles[rect_idx]['hovered'] = False
                hovered_rect = None

def on_mouse_up(event):
    x = canvas.canvasx(event.x)
    y = canvas.canvasy(event.y)
    global rectangles, rect, drawing, selected_rect, selected_rect_index, moving, resizing, current_handle, selecting_area, selection_rect
    if drawing and rect:
        end_x, end_y = x, y
        original_x1 = start_x / scale_ratio
        original_y1 = start_y / scale_ratio
        original_x2 = end_x / scale_ratio
        original_y2 = end_y / scale_ratio
        rectangles.append({
            'id': rect,
            'coords': (start_x, start_y, end_x, end_y),
            'original_coords': (original_x1, original_y1, original_x2, original_y2),
            'hovered': False
        })
        undo_stack.append(('create', rect))
        rect = None
        drawing = False
    elif moving:
        moving = False
        x1, y1, x2, y2 = rectangles[selected_rect_index]['coords']
        rectangles[selected_rect_index]['original_coords'] = (
            x1 / scale_ratio, y1 / scale_ratio, x2 / scale_ratio, y2 / scale_ratio
        )
        undo_stack.append(('move_end', selected_rect_index, rectangles[selected_rect_index]['coords']))
    elif resizing:
        resizing = False
        current_handle = None
        x1, y1, x2, y2 = rectangles[selected_rect_index]['coords']
        rectangles[selected_rect_index]['original_coords'] = (
            x1 / scale_ratio, y1 / scale_ratio, x2 / scale_ratio, y2 / scale_ratio
        )
        undo_stack.append(('resize_end', selected_rect_index, rectangles[selected_rect_index]['coords']))
    elif selecting_area and selection_rect:
        selecting_area = False
        x1, y1, x2, y2 = canvas.coords(selection_rect)
        selected_rects = []
        for idx, rect_info in enumerate(rectangles):
            rx1, ry1, rx2, ry2 = rect_info['coords']
            if x1 <= rx1 <= x2 and y1 <= ry1 <= y2 and x1 <= rx2 <= x2 and y1 <= ry2 <= y2:
                selected_rects.append((idx, rect_info))
        if selected_rects:
            for idx, rect_info in reversed(selected_rects):
                canvas.delete(rect_info['id'])
                rectangles.pop(idx)
            undo_stack.append(('delete_area', selected_rects))
        canvas.delete(selection_rect)
        selection_rect = None

def delete_rectangle():
    global rectangles, selected_rect, selected_rect_index, handles
    if selected_rect is not None:
        canvas.delete(selected_rect)
        for handle_id in handles.values():
            canvas.delete(handle_id)
        handles.clear()
        undo_stack.append(('delete', selected_rect_index, rectangles[selected_rect_index]))
        rectangles.pop(selected_rect_index)
        selected_rect = None
        selected_rect_index = None
    else:
        messagebox.showinfo("提示", "請先選擇要刪除的矩形框")

def save_to_yolo():
    if img is None:
        messagebox.showerror("錯誤", "請先載入圖片")
        return
    filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文字檔", "*.txt")])
    if filepath:
        with open(filepath, 'w') as f:
            for rect_info in rectangles:
                x1, y1, x2, y2 = rect_info['original_coords']
                x_center = ((x1 + x2) / 2) / img_width
                y_center = ((y1 + y2) / 2) / img_height
                width = abs(x2 - x1) / img_width
                height = abs(y2 - y1) / img_height
                f.write(f"0 {x_center} {y_center} {width} {height}\n")
        messagebox.showinfo("保存", "標註已保存為YOLO格式")

def load_from_yolo():
    global rectangles, selected_rect, selected_rect_index, handles
    if img is None:
        messagebox.showerror("錯誤", "請先載入圖片")
        return
    filepath = filedialog.askopenfilename(title="載入標註檔", filetypes=[("文字檔", "*.txt")])
    if filepath:
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            # 清除已有的矩形框等數據
            rectangles.clear()
            selected_rect = None
            selected_rect_index = None
            handles.clear()
            # 清除 Canvas 上的所有內容
            canvas.delete("all")
            # 重新顯示圖片
            display_image()
            for line in lines:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                cls, x_center, y_center, width, height = map(float, parts)
                # 轉換為圖片座標
                x_center *= img_width
                y_center *= img_height
                width *= img_width
                height *= img_height
                x1 = x_center - width / 2
                y1 = y_center - height / 2
                x2 = x_center + width / 2
                y2 = y_center + height / 2
                # 縮放座標
                x1_display = x1 * scale_ratio
                y1_display = y1 * scale_ratio
                x2_display = x2 * scale_ratio
                y2_display = y2 * scale_ratio
                # 繪製矩形框
                rect_id = canvas.create_rectangle(
                    x1_display, y1_display, x2_display, y2_display, outline='green', tags='rectangle'
                )
                rectangles.append({
                    'id': rect_id,
                    'coords': (x1_display, y1_display, x2_display, y2_display),
                    'original_coords': (x1, y1, x2, y2),
                    'hovered': False
                })
            messagebox.showinfo("載入", "標註已載入")
        except Exception as e:
            messagebox.showerror("錯誤", f"無法載入標註檔：{e}")

def undo_action(event=None):
    if not undo_stack:
        return
    action = undo_stack.pop()
    if action[0] == 'create':
        rect_id = action[1]
        idx = next((idx for idx, rect_info in enumerate(rectangles) if rect_info['id'] == rect_id), None)
        if idx is not None:
            canvas.delete(rect_id)
            rectangles.pop(idx)
    elif action[0] == 'delete':
        idx, rect_info = action[1], action[2]
        rect_id = canvas.create_rectangle(*rect_info['coords'], outline='green', tags='rectangle')
        rect_info['id'] = rect_id
        rectangles.insert(idx, rect_info)
    elif action[0] == 'move_start':
        pass
    elif action[0] == 'move_end':
        idx, coords = action[1], action[2]
        canvas.coords(rectangles[idx]['id'], *coords)
        rectangles[idx]['coords'] = coords
    elif action[0] == 'resize_start':
        pass
    elif action[0] == 'resize_end':
        idx, coords = action[1], action[2]
        canvas.coords(rectangles[idx]['id'], *coords)
        rectangles[idx]['coords'] = coords
    elif action[0] == 'delete_area':
        deleted_rects = action[1]
        for idx, rect_info in deleted_rects:
            rect_id = canvas.create_rectangle(*rect_info['coords'], outline='green', tags='rectangle')
            rect_info['id'] = rect_id
            rectangles.insert(idx, rect_info)

def save_action(event=None):
    save_to_yolo()

def on_mouse_wheel(event):
    global zoom_level
    if event.state & 0x0004:
        if event.delta > 0:
            zoom_level = min(zoom_level * 1.1, 3.0)
        else:
            zoom_level = max(zoom_level / 1.1, 0.1)
        display_image()

def on_delete_key(event):
    delete_rectangle()

def create_gui():
    global root, canvas, control_frame
    root = tk.Tk()
    root.title("遮罩編輯器")
    root.bind('<Configure>', on_window_resize)
    root.update()
    root.bind('<Control-z>', undo_action)
    root.bind('<Control-s>', save_action)
    root.bind('<Delete>', on_delete_key)
    control_frame = tk.Frame(root)
    control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
    select_button = tk.Button(control_frame, text="選擇圖片", command=select_image)
    select_button.grid(row=0, column=0, padx=5, pady=5)
    load_button = tk.Button(control_frame, text="載入標註", command=load_from_yolo)
    load_button.grid(row=0, column=1, padx=5, pady=5)
    delete_button = tk.Button(control_frame, text="刪除矩形框", command=delete_rectangle)
    delete_button.grid(row=0, column=2, padx=5, pady=5)
    save_button = tk.Button(control_frame, text="保存標註", command=save_to_yolo)
    save_button.grid(row=1, column=0, padx=5, pady=5)
    canvas_frame = tk.Frame(root)
    canvas_frame.pack(fill=tk.BOTH, expand=True)
    canvas = Canvas(canvas_frame, cursor="cross", bg='white')
    canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
    hbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=canvas.xview)
    hbar.pack(side=tk.BOTTOM, fill=tk.X)
    vbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
    vbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    canvas.bind("<Motion>", on_mouse_move)
    canvas.bind("<MouseWheel>", on_mouse_wheel)
    if os.path.exists(default_image_path):
        load_image(default_image_path)
        display_image()
    root.mainloop()

if __name__ == "__main__":
    create_gui()
