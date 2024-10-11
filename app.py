from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import glob

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ANNOTATIONS_FOLDER'] = 'static/annotations'

# 確保上傳和標註文件夾存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANNOTATIONS_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_default_image')
def get_default_image():
    default_image = 'uploads/default.jpg'  # 設定默認圖片名稱
    return jsonify({'filename': default_image})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    file = request.files['image']
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        return jsonify({'filename': file.filename})
    return jsonify({'error': '未上傳檔案'}), 400

@app.route('/get_image/<filename>')
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/save_annotations', methods=['POST'])
def save_annotations():
    data = request.get_json()
    annotations = data.get('annotations')
    image_name = data.get('imageName')
    if annotations and image_name:
        # 儲存新的標註檔案之前，清除舊的標註
        old_files = glob.glob(os.path.join(app.config['ANNOTATIONS_FOLDER'], '*.txt'))
        for old_file in old_files:
            os.remove(old_file)

        # 儲存新的標註檔案
        annotation_path = os.path.join(app.config['ANNOTATIONS_FOLDER'], f'{image_name}.txt')
        with open(annotation_path, 'w') as f:
            for ann in annotations:
                f.write(' '.join(map(str, ann)) + '\n')
        return jsonify({'status': 'success'})
    return jsonify({'error': '無效資料'}), 400

@app.route('/load_annotations', methods=['POST'])
def load_annotations():
    data = request.get_json()
    image_name = data.get('imageName')
    if image_name:
        annotation_path = os.path.join(app.config['ANNOTATIONS_FOLDER'], f'{image_name}.txt')
        if os.path.exists(annotation_path):
            with open(annotation_path, 'r') as f:
                lines = f.readlines()
            annotations = []
            for line in lines:
                parts = list(map(float, line.strip().split()))
                annotations.append(parts)
            return jsonify({'annotations': annotations})
        else:
            return jsonify({'annotations': []})
    return jsonify({'error': '無效資料'}), 400

if __name__ == '__main__':
    app.run(debug=True)
