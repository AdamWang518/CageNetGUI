let canvas = document.getElementById('imageCanvas');
let ctx = canvas.getContext('2d');
let imageLoader = document.getElementById('imageLoader');
let loadAnnotationsBtn = document.getElementById('loadAnnotations');
let saveAnnotationsBtn = document.getElementById('saveAnnotations');
let deleteRectangleBtn = document.getElementById('deleteRectangle');
let imageName = '';
let image = new Image();
let scaleRatio = 1;

let rectangles = [];
let undoStack = [];
let currentRect = null;
let isDrawing = false;
let selectedRectIndex = null;
let selectedRectIndexes = [];
let isMoving = false;
let isResizing = false;
let currentHandle = null;
let handles = [];
let handleSize = 8;
let startX, startY;
let isSelectingArea = false;
let selectionRect = null;

// 加載默認圖片
window.onload = function () {
    loadImage('/static/uploads/default.jpg');
    // fetch('/get_default_image')
    //     .then(response => response.json())
    //     .then(data => {
    //         let defaultImage = data.filename;
    //         loadImage(defaultImage);
    //     });
};

// 處理圖像上傳
imageLoader.addEventListener('change', handleImageUpload, false);

function handleImageUpload(e) {
    let reader = new FileReader();
    reader.onload = function (event) {
        image.onload = function () {
            scaleCanvas();
            drawImage();
            loadAnnotations();
        }
        image.src = event.target.result;
        imageName = imageLoader.files[0].name;

        // 上傳圖像到伺服器
        let formData = new FormData();
        formData.append('image', imageLoader.files[0]);
        fetch('/upload_image', {
            method: 'POST',
            body: formData
        });
    }
    reader.readAsDataURL(e.target.files[0]);
}

function scaleCanvas() {
    canvas.width = image.width;
    canvas.height = image.height;
    scaleRatio = 1;

    // 根據容器寬度調整畫布大小
    let maxWidth = document.querySelector('.canvas-container').clientWidth;
    if (canvas.width > maxWidth) {
        scaleRatio = maxWidth / canvas.width;
        canvas.width *= scaleRatio;
        canvas.height *= scaleRatio;
    }
}

function loadImage(imageFilename) {
    imageName = `default.jpg`;
    image.src = `${imageFilename}`;
    image.onload = function () {
        scaleCanvas();
        drawImage();
        loadAnnotations();
    };
}

function drawImage() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    drawRectangles();
}

function drawRectangles() {
    rectangles.forEach((rect, index) => {
        ctx.strokeStyle = selectedRectIndexes.includes(index) ? 'red' : (rect.hovered ? 'blue' : 'green');
        ctx.lineWidth = 2;
        ctx.strokeRect(rect.x * scaleRatio, rect.y * scaleRatio, rect.w * scaleRatio, rect.h * scaleRatio);
        if (selectedRectIndexes.includes(index)) {
            drawHandles(rect);
        }
    });
}

function drawHandles(rect) {
    let positions = getHandlePositions(rect);
    positions.forEach(pos => {
        ctx.fillStyle = 'blue';
        ctx.fillRect((pos.x - handleSize / 2) * scaleRatio, (pos.y - handleSize / 2) * scaleRatio, handleSize, handleSize);
    });
}

function getHandlePositions(rect) {
    let x1 = rect.x, y1 = rect.y, x2 = rect.x + rect.w, y2 = rect.y + rect.h;
    return [
        { x: x1, y: y1 },
        { x: (x1 + x2) / 2, y: y1 },
        { x: x2, y: y1 },
        { x: x2, y: (y1 + y2) / 2 },
        { x: x2, y: y2 },
        { x: (x1 + x2) / 2, y: y2 },
        { x: x1, y: y2 },
        { x: x1, y: (y1 + y2) / 2 },
    ];
}

function getHandleAtPoint(x, y, rect) {
    let positions = getHandlePositions(rect);
    for (let i = 0; i < positions.length; i++) {
        let pos = positions[i];
        if (Math.abs(x - pos.x) * scaleRatio <= handleSize && Math.abs(y - pos.y) * scaleRatio <= handleSize) {
            return i;
        }
    }
    return -1;
}

canvas.addEventListener('mousedown', function (e) {
    let mousePos = getMousePos(e);
    startX = mousePos.x / scaleRatio;
    startY = mousePos.y / scaleRatio;

    if (e.shiftKey) {
        // 選擇區域以刪除多個矩形
        isSelectingArea = true;
        selectionRect = { x: startX, y: startY, w: 0, h: 0 };
    } else {
        let handleInfo = getHandleUnderMouse(mousePos);
        if (handleInfo) {
            // 調整大小
            isResizing = true;
            currentHandle = handleInfo.handleIndex;
            selectedRectIndex = handleInfo.rectIndex;
            undoStack.push({ action: 'resize_start', rectIndex: selectedRectIndex, rect: { ...rectangles[selectedRectIndex] } });

            // 將選中的矩形移到列表末尾（頂層）
            let selectedRect = rectangles.splice(selectedRectIndex, 1)[0];
            rectangles.push(selectedRect);
            selectedRectIndex = rectangles.length - 1;
            selectedRectIndexes = [selectedRectIndex];
        } else {
            let rectIndex = getRectUnderMouse(mousePos);
            if (rectIndex !== null) {
                // 移動矩形
                isMoving = true;
                offsetX = mousePos.x / scaleRatio - rectangles[rectIndex].x;
                offsetY = mousePos.y / scaleRatio - rectangles[rectIndex].y;
                undoStack.push({ action: 'move_start', rectIndex: rectIndex, rect: { ...rectangles[rectIndex] } });

                // 將選中的矩形移到列表末尾（頂層）
                let selectedRect = rectangles.splice(rectIndex, 1)[0];
                rectangles.push(selectedRect);
                rectIndex = rectangles.length - 1;

                if (e.ctrlKey || e.metaKey) {
                    // 多選
                    if (!selectedRectIndexes.includes(rectIndex)) {
                        selectedRectIndexes.push(rectIndex);
                    }
                } else {
                    selectedRectIndexes = [rectIndex];
                }
            } else {
                // 開始繪製新矩形
                isDrawing = true;
                currentRect = {
                    x: startX,
                    y: startY,
                    w: 0,
                    h: 0
                };
                // 不立即添加到 rectangles 數組
                selectedRectIndexes = [];
            }
        }
    }
    drawImage();
});

canvas.addEventListener('mousemove', function (e) {
    let mousePos = getMousePos(e);
    let x = mousePos.x / scaleRatio;
    let y = mousePos.y / scaleRatio;

    if (isDrawing) {
        currentRect.w = x - currentRect.x;
        currentRect.h = y - currentRect.y;
        drawImage();
        // 繪製當前正在繪製的矩形
        ctx.strokeStyle = 'green';
        ctx.lineWidth = 2;
        ctx.strokeRect(currentRect.x * scaleRatio, currentRect.y * scaleRatio, currentRect.w * scaleRatio, currentRect.h * scaleRatio);
    } else if (isMoving && selectedRectIndexes.length === 1) {
        let rect = rectangles[selectedRectIndexes[0]];
        rect.x = x - offsetX;
        rect.y = y - offsetY;
        drawImage();
    } else if (isResizing && selectedRectIndex !== null) {
        let rect = rectangles[selectedRectIndex];
        resizeRectangle(rect, currentHandle, x, y);
        drawImage();
    } else if (isSelectingArea && selectionRect) {
        selectionRect.w = x - selectionRect.x;
        selectionRect.h = y - selectionRect.y;
        drawImage();
        drawSelectionRect();
    } else {
        // 懸停效果
        let hovered = false;
        rectangles.forEach((rect, index) => {
            if (isPointInRect(x, y, rect)) {
                if (!rect.hovered) {
                    rect.hovered = true;
                    drawImage();
                }
                hovered = true;
            } else {
                if (rect.hovered) {
                    rect.hovered = false;
                    drawImage();
                }
            }
        });
    }
});

canvas.addEventListener('mouseup', function (e) {
    if (isDrawing) {
        isDrawing = false;
        // 檢查矩形是否有效（寬度和高度都大於等於1）
        if (Math.abs(currentRect.w) >= 1 && Math.abs(currentRect.h) >= 1) {
            // 有效的矩形，添加到 rectangles 數組
            rectangles.push(currentRect);
            selectedRectIndexes = [rectangles.length - 1];
            undoStack.push({ action: 'create', rectIndex: rectangles.length - 1 });
        } else {
            // 無效的矩形，丟棄
            currentRect = null;
        }
    }
    isMoving = false;
    isResizing = false;
    isSelectingArea = false;

    if (selectionRect) {
        // 刪除選區內的矩形
        let x1 = selectionRect.x;
        let y1 = selectionRect.y;
        let x2 = x1 + selectionRect.w;
        let y2 = y1 + selectionRect.h;
        let deletedRects = [];
        for (let i = rectangles.length - 1; i >= 0; i--) {
            let rect = rectangles[i];
            if (rect.x >= Math.min(x1, x2) && rect.y >= Math.min(y1, y2) &&
                rect.x + rect.w <= Math.max(x1, x2) && rect.y + rect.h <= Math.max(y1, y2)) {
                deletedRects.push({ rectIndex: i, rect: rect });
                rectangles.splice(i, 1);
            }
        }
        if (deletedRects.length > 0) {
            undoStack.push({ action: 'delete_area', rects: deletedRects });
        }
        selectionRect = null;
        drawImage();
    }

    if (selectedRectIndex !== null) {
        // 更新撤銷棧
        if (undoStack.length > 0 && undoStack[undoStack.length - 1].action === 'move_start') {
            undoStack.push({ action: 'move_end', rectIndex: selectedRectIndex, rect: { ...rectangles[selectedRectIndex] } });
        }
        if (undoStack.length > 0 && undoStack[undoStack.length - 1].action === 'resize_start') {
            undoStack.push({ action: 'resize_end', rectIndex: selectedRectIndex, rect: { ...rectangles[selectedRectIndex] } });
        }
    }
    drawImage();
});

function resizeRectangle(rect, handleIndex, x, y) {
    switch (handleIndex) {
        case 0:
            rect.w += rect.x - x;
            rect.h += rect.y - y;
            rect.x = x;
            rect.y = y;
            break;
        case 1:
            rect.h += rect.y - y;
            rect.y = y;
            break;
        case 2:
            rect.w = x - rect.x;
            rect.h += rect.y - y;
            rect.y = y;
            break;
        case 3:
            rect.w = x - rect.x;
            break;
        case 4:
            rect.w = x - rect.x;
            rect.h = y - rect.y;
            break;
        case 5:
            rect.h = y - rect.y;
            break;
        case 6:
            rect.w += rect.x - x;
            rect.h = y - rect.y;
            rect.x = x;
            break;
        case 7:
            rect.w += rect.x - x;
            rect.x = x;
            break;
    }
}

function getHandleUnderMouse(pos) {
    for (let i = rectangles.length - 1; i >= 0; i--) {
        let rect = rectangles[i];
        let handleIndex = getHandleAtPoint(pos.x / scaleRatio, pos.y / scaleRatio, rect);
        if (handleIndex !== -1 && selectedRectIndexes.includes(i)) {
            return { rectIndex: i, handleIndex: handleIndex };
        }
    }
    return null;
}

function getMousePos(evt) {
    let rect = canvas.getBoundingClientRect();
    return {
        x: evt.clientX - rect.left,
        y: evt.clientY - rect.top
    };
}

function getRectUnderMouse(pos) {
    for (let i = rectangles.length - 1; i >= 0; i--) {
        let rect = rectangles[i];
        if (isPointInRect(pos.x / scaleRatio, pos.y / scaleRatio, rect)) {
            return i;
        }
    }
    return null;
}

function isPointInRect(x, y, rect) {
    return x >= rect.x && x <= rect.x + rect.w &&
        y >= rect.y && y <= rect.y + rect.h;
}

function drawSelectionRect() {
    ctx.strokeStyle = 'blue';
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 3]);
    ctx.strokeRect(selectionRect.x * scaleRatio, selectionRect.y * scaleRatio, selectionRect.w * scaleRatio, selectionRect.h * scaleRatio);
    ctx.setLineDash([]);
}

deleteRectangleBtn.addEventListener('click', function () {
    deleteSelectedRectangles();
});

function deleteSelectedRectangles() {
    if (selectedRectIndexes.length > 0) {
        let deletedRects = [];
        selectedRectIndexes.sort((a, b) => b - a); // 從高到低刪除
        selectedRectIndexes.forEach(index => {
            deletedRects.push({ rectIndex: index, rect: rectangles[index] });
            rectangles.splice(index, 1);
        });
        undoStack.push({ action: 'delete', rects: deletedRects });
        selectedRectIndexes = [];
        drawImage();
    } else {
        alert('請先選擇要刪除的矩形框');
    }
}

saveAnnotationsBtn.addEventListener('click', function () {
    if (!imageName) {
        alert('請先載入圖片');
        return;
    }
    let annotations = rectangles
        .filter(rect => Math.abs(rect.w) >= 1 && Math.abs(rect.h) >= 1) // 過濾有效的矩形
        .map(rect => {
            let x_center = (rect.x + rect.w / 2) / image.width;
            let y_center = (rect.y + rect.h / 2) / image.height;
            let width = Math.abs(rect.w) / image.width;
            let height = Math.abs(rect.h) / image.height;
            return [0, x_center.toFixed(6), y_center.toFixed(6), width.toFixed(6), height.toFixed(6)];
        });
    fetch('/save_annotations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ annotations: annotations, imageName: imageName })
    }).then(response => response.json()).then(data => {
        if (data.status === 'success') {
            alert('標註已儲存');
        }
    });
});

loadAnnotationsBtn.addEventListener('click', function () {
    if (!imageName) {
        alert('請先載入圖片');
        return;
    }
    loadAnnotations();
});

function loadAnnotations() {
    fetch('/load_annotations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageName: imageName })
    }).then(response => response.json()).then(data => {
        rectangles = [];
        data.annotations.forEach(ann => {
            let [cls, x_center, y_center, width, height] = ann;
            let rect = {
                x: (x_center - width / 2) * image.width,
                y: (y_center - height / 2) * image.height,
                w: width * image.width,
                h: height * image.height,
                hovered: false
            };
            rectangles.push(rect);
        });
        drawImage();
    });
}

// 鍵盤快捷鍵
canvas.addEventListener('keydown', function (e) {
    if (e.ctrlKey && e.key === 'z') {
        e.preventDefault();
        undoAction();
    }
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveAnnotationsBtn.click();
    }
    if (e.key === 'Delete') {
        e.preventDefault();
        deleteSelectedRectangles();
    }
});

function undoAction() {
    if (undoStack.length === 0) return;
    let action = undoStack.pop();
    switch (action.action) {
        case 'create':
            rectangles.splice(action.rectIndex, 1);
            break;
        case 'delete':
            action.rects.forEach(item => {
                rectangles.splice(item.rectIndex, 0, item.rect);
            });
            break;
        case 'move_start':
            // 無操作
            break;
        case 'move_end':
            rectangles[action.rectIndex] = action.rect;
            break;
        case 'resize_start':
            // 無操作
            break;
        case 'resize_end':
            rectangles[action.rectIndex] = action.rect;
            break;
        case 'delete_area':
            action.rects.forEach(item => {
                rectangles.splice(item.rectIndex, 0, item.rect);
            });
            break;
    }
    drawImage();
}
