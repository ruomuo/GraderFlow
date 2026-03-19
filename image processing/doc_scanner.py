import cv2
import numpy as np
import os

def find_document_contour(image):
    """
    在图像中查找文档的轮廓。

    :param image: 输入的图像
    :return: 文档的轮廓坐标
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # 降低Canny阈值以检测较弱的边缘
    edged = cv2.Canny(blurred, 75, 200)

    # 使用闭合操作连接断开的边缘
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    # 在闭合后的图像上查找轮廓
    contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            return approx
    return None

def perspective_transform(image, pts):
    """
    对图像进行透视变换。

    :param image: 输入的图像
    :param pts: 轮廓的四个顶点
    :return: 变换后的图像
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=2)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=2)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped

def enhance_image(image):
    """
    增强图像，使其更清晰。

    :param image: 输入的图像
    :return: 增强后的图像
    """
    warped_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sharpened = cv2.adaptiveThreshold(warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return sharpened

def scan_document(image_path):
    """
    加载图像，执行文档扫描和增强。

    :param image_path: 图像文件的路径
    :return: 扫描并增强后的图像
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"无法加载图像: {image_path}")
        return None

    original_image = image.copy()
    contour = find_document_contour(image)

    if contour is None:
        print("未找到文档轮廓。")
        return None

    transformed_image = perspective_transform(original_image, contour)
    
    # 注意：原始代码中未调用 enhance_image，如果你需要二值化效果，可以取消下面这行的注释
    # transformed_image = enhance_image(transformed_image)

    return original_image, transformed_image

if __name__ == '__main__':
    # 创建一个用于测试的虚拟文档图像
    def create_dummy_image(file_path):
        width, height = 800, 1000
        image = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        # 绘制一些文本
        cv2.putText(image, "This is a test document.", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(image, "The quick brown fox jumps over the lazy dog.", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(image, "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        # 创建一个倾斜的矩形
        pts1 = np.float32([[50, 50], [width - 50, 100], [20, height - 20], [width - 20, height - 50]])
        pts2 = np.float32([[0, 0], [width, 0], [0, height], [width, height]])

        # 应用透视变换来模拟倾斜的文档
        matrix = cv2.getPerspectiveTransform(pts2, pts1)
        transformed_image = cv2.warpPerspective(image, matrix, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(150, 150, 150))
        
        cv2.imwrite(file_path, transformed_image)

    # 如果需要生成测试图片，取消下面两行的注释
    # dummy_image_path = "dummy_document.png"
    # create_dummy_image(dummy_image_path)

    # --- 这里需要修改为您本地的实际路径 ---
    image_path = "E:\\code_space\\code_python\\MarkingSystem\\test_img\\answer_163.png" 
    
    result = scan_document(image_path)

    if result is not None:
        original, transformed = result
        
        # 定义输出目录
        output_dir = "e:/code_space/code_python/MarkingSystem/processed_img/"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 构建输出文件路径
        base_name = os.path.basename(image_path)
        file_name, file_ext = os.path.splitext(base_name)
        output_path = os.path.join(output_dir, f"{file_name}_processed{file_ext}")

        # 保存处理后的图像
        cv2.imwrite(output_path, transformed)
        print(f"处理后的图像已保存到: {output_path}")

        # 显示结果
        cv2.imshow("Original Image", cv2.resize(original, (400, 500)))
        cv2.imshow("Transformed Image", cv2.resize(transformed, (400, 500)))
        
        print("按任意键关闭窗口...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()