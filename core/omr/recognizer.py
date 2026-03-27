import cv2
import os
import sys

# 添加项目根目录到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import re
import heapq
import numpy as np
from core.omr.question_parser import parse_question_types, parse_multiple_choice_answers

def detect_rectangle_filling(roi, debug=False, is_top_edge=False, is_bottom_edge=False):
    """
    改进的矩形填涂检测算法
    
    参数:
        roi: 矩形区域的二值图像
        debug: 是否显示调试信息
        is_top_edge: 是否位于图像顶部边缘 (易受裁剪噪声影响)
        is_bottom_edge: 是否位于图像底部边缘
    
    返回:
        bool: 是否填涂
    """
    h, w = roi.shape
    
    # 方法1: 边框去除 + 内部区域分析
    # 去除边框（假设边框宽度为2-3像素）
    border_width = max(2, min(w//10, h//10))  # 动态计算边框宽度
    inner_roi = roi[border_width:-border_width, border_width:-border_width]
    
    if inner_roi.size == 0:
        return False
    
    inner_filled_ratio = cv2.countNonZero(inner_roi) / inner_roi.size

    relaxed_edge = is_top_edge or is_bottom_edge
    min_inner_ratio = 0.15 if relaxed_edge else 0.2
    if inner_filled_ratio < min_inner_ratio:
        return False
    
    # 方法2: 连通域分析
    # 查找连通域
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(inner_roi, connectivity=8)
    
    # 排除背景（标签0），计算最大连通域的面积
    if num_labels > 1:
        # 获取除背景外最大的连通域面积
        max_area = max(stats[1:, cv2.CC_STAT_AREA])
        max_area_ratio = max_area / inner_roi.size
    else:
        max_area_ratio = 0
    
    # 方法3: 中心区域密度分析
    # 分析矩形中心区域的填涂情况
    center_h, center_w = h//2, w//2
    quarter_h, quarter_w = h//4, w//4
    center_roi = roi[center_h-quarter_h:center_h+quarter_h, center_w-quarter_w:center_w+quarter_w]
    
    if center_roi.size > 0:
        center_filled_ratio = cv2.countNonZero(center_roi) / center_roi.size
    else:
        center_filled_ratio = 0
    
    # 方法4: 边缘对比分析
    # 比较边缘区域和内部区域的像素密度差异
    edge_roi = roi.copy()
    edge_roi[border_width:-border_width, border_width:-border_width] = 0  # 将内部区域置零
    edge_filled_ratio = cv2.countNonZero(edge_roi) / (roi.size - inner_roi.size) if (roi.size - inner_roi.size) > 0 else 0
    
    # 方法5: 形态学检查 - 验证填涂的连续性
    # 使用形态学操作来检查填涂区域的连续性
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    morphed = cv2.morphologyEx(inner_roi, cv2.MORPH_CLOSE, kernel)
    morphed_ratio = cv2.countNonZero(morphed) / inner_roi.size
    
    # 计算形态学操作前后的差异，差异小说明填涂连续性好
    morphology_consistency = abs(morphed_ratio - inner_filled_ratio) < 0.1

    # 综合判断 - 提高阈值以减少误识别
    # 设置更严格的阈值条件
    inner_ratio_th = 0.3 if relaxed_edge else 0.5
    max_area_th = 0.2 if relaxed_edge else 0.3
    center_ratio_th = 0.3 if relaxed_edge else 0.6
    edge_ratio_mul = 1.2 if relaxed_edge else 2.0
    dual_inner_th = 0.25 if relaxed_edge else 0.4
    dual_center_th = 0.2 if relaxed_edge else 0.5

    conditions = [
        inner_filled_ratio > inner_ratio_th,
        max_area_ratio > max_area_th,
        center_filled_ratio > center_ratio_th,
        inner_filled_ratio > edge_filled_ratio * edge_ratio_mul,
        inner_filled_ratio > dual_inner_th and center_filled_ratio > dual_center_th,
        morphology_consistency
    ]

    filled_score = sum(conditions)
    required_score = 3 if relaxed_edge else 4
    is_filled = filled_score >= required_score
    if not is_filled and relaxed_edge:
        if inner_filled_ratio >= 0.18 and max_area_ratio >= 0.11 and center_filled_ratio >= 0.05 and morphology_consistency:
            is_filled = True
    
    if debug:
        print(f"填涂检测详情:")
        print(f"  内部填涂密度: {inner_filled_ratio:.3f} (阈值: >{inner_ratio_th})")
        print(f"  最大连通域占比: {max_area_ratio:.3f} (阈值: >{max_area_th})")
        print(f"  中心区域密度: {center_filled_ratio:.3f} (阈值: >{center_ratio_th})")
        print(f"  边缘区域密度: {edge_filled_ratio:.3f}")
        print(f"  内部/边缘密度比: {inner_filled_ratio/edge_filled_ratio if edge_filled_ratio > 0 else float('inf'):.2f} (阈值: >{edge_ratio_mul})")
        print(f"  形态学一致性: {morphology_consistency} (差异: {abs(morphed_ratio - inner_filled_ratio):.3f})")
        print(f"  满足条件数: {filled_score}/6")
        print(f"  最终结果: {'填涂' if is_filled else '未填涂'}")
    
    return is_filled

def deskew_image(image, debug=False):
    """
    图像纠偏算法
    基于霍夫变换检测直线进行纠偏，比基于轮廓的方法更鲁棒
    """
    if image is None:
        return image
        
    h, w = image.shape[:2]
    
    # 1. 预处理
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    # 边缘检测
    # 使用Canny边缘检测
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # 2. 霍夫直线检测
    # minLineLength: 线段最小长度 (设置为宽度的1/10，确保检测到足够长的线，如横线或文字行)
    # maxLineGap: 线段最大间隔 (允许断开的线被视为同一条线)
    min_line_length = w // 10
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, minLineLength=min_line_length, maxLineGap=20)
    
    if lines is None:
        if debug: print("未检测到直线，尝试使用轮廓法兜底...")
        # 兜底逻辑：如果直线检测失败，尝试使用轮廓法（针对白纸黑背景优化）
        return _deskew_contour_fallback(image, gray, debug)
        
    # 3. 计算角度
    angles = []
    line_lengths = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1: # 垂直线，忽略
            continue
        
        angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        # 只保留接近水平的线 (-20 到 20 度)
        if -20 < angle < 20:
            angles.append(angle)
            line_lengths.append(length)
            
    if not angles:
        if debug: print("未检测到水平直线，尝试使用轮廓法兜底...")
        return _deskew_contour_fallback(image, gray, debug)
        
    # 4. 计算加权平均角度（长度越长权重越大）
    # 或者使用直方图统计
    
    # 简单的中位数
    median_angle = np.median(angles)
    mean_angle = np.mean(angles)
    
    # 加权平均
    weighted_angle = np.average(angles, weights=line_lengths)
    
    if debug:
        print(f"检测到 {len(angles)} 条水平线")
        print(f"角度统计: Min={np.min(angles):.2f}, Max={np.max(angles):.2f}, Median={median_angle:.2f}, Mean={mean_angle:.2f}, Weighted={weighted_angle:.2f}")
        # print(f"前10个角度: {angles[:10]}")
    
    # 使用加权平均可能更准确，因为长线（表格边框）更可靠
    rotation_angle = weighted_angle
        
    # 限制最大旋转角度
    if abs(rotation_angle) > 15:
        if debug: print(f"角度 {rotation_angle:.2f} 过大，忽略")
        return image
        
    if abs(rotation_angle) < 0.1: # 忽略微小偏斜
        return image
        
    print(f"执行图像纠偏(霍夫变换): 旋转 {rotation_angle:.2f} 度")
        
    # 5. 执行旋转
    (cX, cY) = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D((cX, cY), rotation_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated

def _calculate_skew_projection(image, debug=False):
    """
    基于水平投影方差的纠偏角度计算
    """
    h, w = image.shape[:2]
    
    # 缩小图片以加速计算，保留足够的细节即可
    scale = 1000 / max(h, w)
    if scale < 1:
        img_small = cv2.resize(image, None, fx=scale, fy=scale)
    else:
        img_small = image.copy()
        
    if len(img_small.shape) == 3:
        gray = cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_small
        
    # 使用Canny边缘检测，关注文字行和表格线
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    best_angle = 0
    max_variance = 0
    
    # 粗搜索：-5 到 5 度，步长 0.5
    angles = np.arange(-5, 5.1, 0.5)
    best_coarse_angle = 0
    
    (h_s, w_s) = edges.shape[:2]
    (cX, cY) = (w_s // 2, h_s // 2)
    
    for angle in angles:
        M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
        rotated = cv2.warpAffine(edges, M, (w_s, h_s), flags=cv2.INTER_NEAREST)
        
        # 计算水平投影
        projection = np.sum(rotated, axis=1)
        variance = np.var(projection)
        
        if variance > max_variance:
            max_variance = variance
            best_coarse_angle = angle
            
    # 精搜索：在最佳粗角度附近 +/- 0.5 度，步长 0.1
    max_variance = 0 # Reset or keep? Better keep comparing.
    # 其实可以直接在 best_coarse_angle 附近搜，但为了简单，重新比较 variance 也没问题
    # 这里我们只关心在 best_coarse_angle 附近的微调
    
    fine_angles = np.arange(best_coarse_angle - 0.5, best_coarse_angle + 0.6, 0.1)
    
    for angle in fine_angles:
        M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
        rotated = cv2.warpAffine(edges, M, (w_s, h_s), flags=cv2.INTER_NEAREST)
        
        projection = np.sum(rotated, axis=1)
        variance = np.var(projection)
        
        if variance > max_variance:
            max_variance = variance
            best_angle = angle
            
    if debug:
        print(f"投影法检测角度: {best_angle:.2f}")
        
    return best_angle

def deskew_image(image, debug=False):
    """
    图像纠偏算法
    结合霍夫变换和投影法，优先使用投影法（更鲁棒）
    """
    if image is None:
        return image
        
    # 尝试使用投影法（通常对文档图像更准确）
    try:
        projection_angle = _calculate_skew_projection(image, debug)
        if abs(projection_angle) > 0.1:
             h, w = image.shape[:2]
             print(f"执行图像纠偏(投影法): 旋转 {projection_angle:.2f} 度")
             (cX, cY) = (w // 2, h // 2)
             M = cv2.getRotationMatrix2D((cX, cY), projection_angle, 1.0)
             return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception as e:
        if debug: print(f"投影法纠偏失败: {e}，尝试使用霍夫变换")
        
    # 以下是原有的霍夫变换逻辑（作为备选）
    h, w = image.shape[:2]
    """
    基于轮廓的纠偏兜底方案
    """
    h, w = image.shape[:2]
    
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 使用普通的二值化来检测白纸（假设背景较暗）
    # 如果背景是黑色，纸是白色，THRESH_BINARY会把纸变成白色
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image
        
    # 筛选大轮廓
    min_area = w * h * 0.1 # 至少10%面积
    valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
    
    if not valid_contours:
        return image
        
    largest_contour = max(valid_contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(largest_contour)
    angle = rect[-1]
    
    if angle < 45:
        rotation_angle = angle
    else:
        rotation_angle = angle - 90
        
    if abs(rotation_angle) > 15 or abs(rotation_angle) < 0.1:
        return image
        
    print(f"执行图像纠偏(轮廓兜底): 旋转 {rotation_angle:.2f} 度")
    (cX, cY) = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D((cX, cY), rotation_angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def recognize_answer_sheet(
    image_path,
    top_n=20,
    question_types=None,
    start_question_num=1,
    options_config=None,
    area_keep_ratio=0.6,
    area_gap_factor=3.0,
    min_valid_ratio=0.5,
    layout: str = "row",
    global_box=None,
):
    """
    识别答题卡答案，支持单选题和多选题，支持动态选项数量
    
    参数:
        image_path: 图片路径
        top_n: 检测轮廓数量
        question_types: 题目类型配置，格式为 {题号: 'single'/'multiple'}
                       如果为None，默认所有题目为单选题
        start_question_num: 起始题号
        options_config: 选项配置，格式为 {题号: 选项个数}
                       如果为None，默认所有题目为4个选项
    
    返回:
        dict: 识别结果字典，键为题号，值为答案（单选为字符串，多选为列表）
    其他:
        area_keep_ratio: 面积保留比例阈值（相对最大面积），用于过滤明显偏小的误检
        area_gap_factor: 面积倍数阈值（最大/次大），用于识别“差距过大”的情形并抑制误警告
        min_valid_ratio: 相对参考面积的最小有效比例，用于剔除“小框噪声”（默认相对参考面积的 50%）
        layout: 题列布局，"row"=一行一题（默认），"column"=一列一题
        global_box: 该图片在原图中的全局坐标 (cx, cy, w, h) normalized，用于坐标映射
    """
    # 如果没有提供题目类型配置，默认所有题目为单选题
    if question_types is None:
        question_types = {}
    
    # 如果没有提供选项配置，默认所有题目为4个选项
    if options_config is None:
        options_config = {}
    
    debug_mode = False
    
    # 读取图像并初始化参数
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: 无法读取图片 {image_path}")
        return {}, {}

    # 应用图像纠偏
    print(f"正在对 {os.path.basename(image_path)} 进行纠偏处理...")
    image = deskew_image(image, debug=False)
    
    height, width, _ = image.shape
    # cv2.imshow("01. Original Image", image)
    # cv2.waitKey(0)

    # 预处理
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # cv2.imshow("02. Grayscale", gray)
    # cv2.waitKey(0)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # cv2.imshow("03. Gaussian Blur", blurred)
    # cv2.waitKey(0)

    thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # 【Fix】边缘遮罩：清除图像边缘的噪声 (特别是裁剪产生的黑边)
    # 这些黑边在二值化后变成白色，容易被误判为填涂
    # 减小遮罩宽度，避免误伤紧凑裁剪的边缘填涂
    h_img, w_img = thresh.shape
    mask_margin = 2
    top_strip = thresh[:mask_margin, :]
    bottom_strip = thresh[-mask_margin:, :]
    left_strip = thresh[:, :mask_margin]
    right_strip = thresh[:, -mask_margin:]
    if top_strip.size and (cv2.countNonZero(top_strip) / float(top_strip.size)) > 0.85:
        thresh[:mask_margin, :] = 0
    if bottom_strip.size and (cv2.countNonZero(bottom_strip) / float(bottom_strip.size)) > 0.85:
        thresh[-mask_margin:, :] = 0
    if left_strip.size and (cv2.countNonZero(left_strip) / float(left_strip.size)) > 0.85:
        thresh[:, :mask_margin] = 0
    if right_strip.size and (cv2.countNonZero(right_strip) / float(right_strip.size)) > 0.85:
        thresh[:, -mask_margin:] = 0

    # 检测轮廓
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[0] if len(contours) == 2 else contours[1]

    # 绘制所有检测到的轮廓
    contour_img = image.copy()
    # cv2.drawContours(contour_img, contours, -1, (0, 255, 0), 2)
    # cv2.imshow("05. All Contours", contour_img)
    # cv2.waitKey(0)

    # 改进的轮廓筛选策略 - 不使用Top N限制，而是基于特征筛选
    answer_contours = []
    contour_areas = []
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = w / float(h)
        area = cv2.contourArea(cnt)
        
        # 基本几何特征筛选
        # 对于矩形填涂框，放宽宽高比限制，降低面积阈值
        if (0.3 < aspect_ratio < 2.5 and
            area > 300 and
            w > 8 and h > 8):
            answer_contours.append((x, y, w, h))
            contour_areas.append(area)
            # print(f"有效轮廓: X={x} Y={y} W={w} H={h} 面积={area} 宽高比={aspect_ratio:.2f}")
    
    # print(f"初步筛选后的轮廓数量: {len(answer_contours)}")
    
    # 如果轮廓数量过多，使用面积和位置进一步筛选
    if len(answer_contours) > top_n:
        # 计算面积的中位数，过滤异常大小的轮廓
        median_area = np.median(contour_areas)
        area_std = np.std(contour_areas)
        
        # 保留面积在合理范围内的轮廓
        filtered_contours = []
        for i, (x, y, w, h) in enumerate(answer_contours):
            area = contour_areas[i]
            # 保留面积在中位数±2倍标准差范围内的轮廓
            if abs(area - median_area) <= 2 * area_std:
                filtered_contours.append((x, y, w, h))
        
        answer_contours = filtered_contours
        # print(f"面积筛选后的轮廓数量: {len(answer_contours)}")

    if answer_contours:
        median_w = np.median([c[2] for c in answer_contours])
        median_h = np.median([c[3] for c in answer_contours])
        if median_w > 0 and median_h > 0:
            min_w = median_w * 0.7
            min_h = median_h * 0.7
            answer_contours = [(x, y, w, h) for (x, y, w, h) in answer_contours if not (w < min_w or h < min_h)]
    
    # 按位置排序（从上到下，从左到右）
    answer_contours.sort(key=lambda cnt: (cnt[1], cnt[0]))

    # Normalize layout early
    layout = str(layout).lower().strip()
    print(f"DEBUG: Layout='{layout}', Contours={len(answer_contours)}")

    is_column_filtered = False

    # 【New】列布局预处理：基于列分组过滤多余的轮廓 (如题号)
    if layout == "column" and answer_contours:
        print(f"DEBUG: Performing Column Filtering. Total contours: {len(answer_contours)}")
        # 1. 按X坐标分组 (列聚类)
        # 计算平均宽度用于阈值
        avg_w_local = np.median([c[2] for c in answer_contours])
        col_threshold_local = avg_w_local * 0.8
        print(f"DEBUG: Avg W: {avg_w_local}, Threshold: {col_threshold_local}")
        
        # 简单的1D聚类
        sorted_by_x = sorted(answer_contours, key=lambda c: c[0])
        cols = []
        if sorted_by_x:
            current_col = [sorted_by_x[0]]
            for c in sorted_by_x[1:]:
                if c[0] - current_col[-1][0] < col_threshold_local:
                    current_col.append(c)
                else:
                    cols.append(current_col)
                    current_col = [c]
            cols.append(current_col)
        
        print(f"DEBUG: Found {len(cols)} columns.")

        # 2. 对每一列进行过滤
        filtered_contours_col = []
        for i, col_contours in enumerate(cols):
            # 按Y排序
            col_contours.sort(key=lambda c: c[1])
            print(f"DEBUG: Col {i} has {len(col_contours)} contours. Y-coords: {[c[1] for c in col_contours]}")
            
            # 获取该列对应的题号 (近似)以确定选项数

            # 注意：这里还没有精确的题号映射，只能根据options_config的全局情况估算
            # 或者简单地假设如果是 5 个轮廓但只需要 4 个，就去掉最上面的
            
            # 获取最大可能的选项数 (通常是4)
            max_opts = 4
            if options_config:
                max_opts = max(options_config.values())
            
            # 策略1: 面积/宽度异常过滤 (响应用户要求)
            # 计算该列的中位数面积
            col_areas = [c[2] * c[3] for c in col_contours]
            median_area_col = np.median(col_areas)
            
            # 过滤掉面积差异过大的轮廓 (比如 < 0.2x 或 > 4.0x)
            # 注意：填涂后的框面积会变大，所以上限要宽容
            valid_contours = []
            for i, c in enumerate(col_contours):
                area = c[2] * c[3]
                if 0.2 * median_area_col <= area <= 4.0 * median_area_col:
                    valid_contours.append(c)
                elif debug_mode:
                    print(f"  [Filter] Dropping contour at {c[0]},{c[1]} Area={area} (Median={median_area_col}) - Size Mismatch")
            
            col_contours = valid_contours
            
            # 策略2: 数量限制 (去掉顶部的题号)
            if len(col_contours) > max_opts:
                # 如果数量超过预期，且顶部轮廓距离第二个轮廓较远，或者就是多余的
                # 简单粗暴：去掉最上面的 N 个
                drop_count = len(col_contours) - max_opts
                if debug_mode:
                    print(f"  [Filter] Column has {len(col_contours)} contours (Expected {max_opts}). Dropping top {drop_count}.")
                col_contours = col_contours[drop_count:]
            
            filtered_contours_col.extend(col_contours)
            
        # 更新 answer_contours
        # 重新按位置排序
        answer_contours = sorted(filtered_contours_col, key=lambda cnt: (cnt[1], cnt[0]))
        if debug_mode:
             print(f"列布局预处理后轮廓数: {len(answer_contours)}")
        
        # 【重要】确保后续逻辑能感知到这已经是清洗过的 contour 集合
        # 尤其是 Y轴分段 逻辑，不应该再尝试猜测是否缺少第一行
        is_column_filtered = True
        
    # 绘制筛选后的有效轮廓
    filtered_img = image.copy()
    for (x, y, w, h) in answer_contours:
        cv2.rectangle(filtered_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
    # cv2.imshow("06. Filtered Contours", filtered_img)
    # cv2.waitKey(0)

    # 按位置排序（从上到下，从左到右）
    # print(answer_contours)
    # answer_contours = sorted(answer_contours, key=lambda x: (x[1]//60, x[0]))
    # print(answer_contours)

    # 分析填涂情况 - 支持多选题
    results = {}
    options = []

    # 准备结果可视化图像
    result_img = image.copy()

    default_option_count = 4
    if answer_contours and not options_config:
        x_positions_all = [x for (x, y, w, h) in answer_contours]
        avg_w_local = np.median([w for (x, y, w, h) in answer_contours])
        col_threshold_local = avg_w_local * 0.8 if avg_w_local > 0 else 0
        unique_cols_local = []
        for x0 in sorted(set(x_positions_all)):
            if not unique_cols_local or abs(x0 - unique_cols_local[-1]) > col_threshold_local:
                unique_cols_local.append(x0)
        if len(unique_cols_local) >= 2:
            default_option_count = len(unique_cols_local)

    if answer_contours:
        avg_h = sum([h for (x, y, w, h) in answer_contours]) / len(answer_contours) if answer_contours else 20
        avg_w = sum([w for (x, y, w, h) in answer_contours]) / len(answer_contours) if answer_contours else 20
        base_min_x = min(x for (x, y, w, h) in answer_contours)
        base_max_right = max(x + w for (x, y, w, h) in answer_contours)

        layout = str(layout).lower().strip()
        if layout not in ("row", "column"):
            layout = "row"

        if layout == "row":
            expected_option_count_global = default_option_count
            if options_config:
                try:
                    expected_option_count_global = int(np.median(list(options_config.values())))
                except Exception:
                    expected_option_count_global = default_option_count

            x_positions = [x for (x, y, w, h) in answer_contours]
            unique_cols = []
            col_threshold = avg_w * 0.8
            for x0 in sorted(set(x_positions)):
                if not unique_cols or abs(x0 - unique_cols[-1]) > col_threshold:
                    unique_cols.append(x0)

            if len(unique_cols) >= 2 and len(unique_cols) < expected_option_count_global:
                col_steps = [unique_cols[i + 1] - unique_cols[i] for i in range(len(unique_cols) - 1)]
                step_estimate = float(np.median(col_steps)) if col_steps else 0.0
                if step_estimate > max(avg_w * 0.6, 10):
                    projected_right = int(base_min_x + step_estimate * expected_option_count_global)
                    if projected_right > base_max_right:
                        base_max_right = min(projected_right, width - 1)

            y_positions = [y for (x, y, w, h) in answer_contours]
            unique_rows = []
            row_threshold = avg_h * 0.8
            for y in sorted(set(y_positions)):
                if not unique_rows or abs(y - unique_rows[-1]) > row_threshold:
                    unique_rows.append(y)

            row_groups = {i: [] for i in range(len(unique_rows))}
            for cnt in answer_contours:
                y = cnt[1]
                row_index = None
                for i, row_y in enumerate(unique_rows):
                    if abs(y - row_y) <= row_threshold:
                        row_index = i
                        break
                if row_index is not None:
                    row_groups[row_index].append(cnt)

            filtered = []
            for row_index, row_contours in row_groups.items():
                q_num = start_question_num + row_index
                expected_count = options_config.get(q_num, default_option_count) if options_config else default_option_count
                row_contours.sort(key=lambda c: c[0])
                if len(row_contours) > expected_count:
                    if base_max_right > base_min_x:
                        section_width = (base_max_right - base_min_x) / expected_count
                    else:
                        section_width = 0
                    if section_width > 0:
                        slot_centers = [base_min_x + (i + 0.5) * section_width for i in range(expected_count)]
                        selected = []
                        used = set()
                        for slot in slot_centers:
                            best_idx = None
                            best_dist = float('inf')
                            for idx, c in enumerate(row_contours):
                                if idx in used:
                                    continue
                                center_x = c[0] + c[2] / 2
                                dist = abs(center_x - slot)
                                if dist < best_dist:
                                    best_dist = dist
                                    best_idx = idx
                            if best_idx is not None and best_dist <= section_width * 0.6:
                                used.add(best_idx)
                                selected.append(row_contours[best_idx])
                        if len(selected) >= expected_count:
                            row_contours = selected
                        else:
                            row_contours = row_contours[:expected_count]
                    else:
                        row_contours = row_contours[:expected_count]
                filtered.extend(row_contours)

            if filtered:
                answer_contours = filtered
                avg_h = sum([h for (x, y, w, h) in answer_contours]) / len(answer_contours) if answer_contours else 20
                avg_w = sum([w for (x, y, w, h) in answer_contours]) / len(answer_contours) if answer_contours else 20

        max_right = max(x + w for (x, y, w, h) in answer_contours)
        max_bottom = max(y + h for (x, y, w, h) in answer_contours)
        min_x = min(x for (x, y, w, h) in answer_contours)
        min_y = min(y for (x, y, w, h) in answer_contours)
        if layout == "row":
            min_x = base_min_x
            max_right = base_max_right

        if layout == "row":
            y_positions = [y for (x, y, w, h) in answer_contours]
            unique_rows = []
            row_threshold = avg_h * 0.8
            for y in sorted(set(y_positions)):
                if not unique_rows or abs(y - unique_rows[-1]) > row_threshold:
                    unique_rows.append(y)
            question_total = len(unique_rows)
        else:
            x_positions = [x for (x, y, w, h) in answer_contours]
            unique_cols = []
            col_threshold = avg_w * 0.8
            for x0 in sorted(set(x_positions)):
                if not unique_cols or abs(x0 - unique_cols[-1]) > col_threshold:
                    unique_cols.append(x0)
            question_total = len(unique_cols)
    else:
        print("警告：未检测到任何填涂区域")
        return results

    # 存储每个题目的所有选项信息
    question_options = {}
    
    # 补偿缺失的选项轮廓
    compensated_contours_set = set()  # 记录补偿的轮廓
    
    def compensate_missing_options(contours, layout_type="row", avg_w=20, avg_h=20, max_rows=None, is_filtered=False):
        """补偿缺失的选项轮廓"""
        compensated_contours = list(contours)
        
        if layout_type == "row":
            return compensated_contours

        elif layout_type == "column":
            # 一列一题模式补偿逻辑：基于全局Y轴聚类
            # 1. 收集所有轮廓的Y坐标并聚类，确定“标准行”
            all_y_centers = [y + h/2 for (x, y, w, h) in contours]
            if not all_y_centers:
                return compensated_contours

            # 简单的1D聚类找到Y轴行坐标
            all_y_centers.sort()
            y_clusters = []
            cluster_threshold = max(avg_h * 0.7, 12)
            
            for y_c in all_y_centers:
                if not y_clusters:
                    y_clusters.append([y_c])
                else:
                    if abs(y_c - np.mean(y_clusters[-1])) < cluster_threshold:
                        y_clusters[-1].append(y_c)
                    else:
                        y_clusters.append([y_c])
            
            unique_rows_y = [int(np.mean(c)) for c in y_clusters]
            
            # 【Fix】检测并补全缺失的首行 (针对裁剪导致的顶部选项缺失)
            # 如果检测到的第一行位置较大，且行间距稳定，说明第一行可能丢失
            # 但必须受到 max_rows 的限制，避免错误地把已过滤的题号区域当做缺失行补回来
            if len(unique_rows_y) >= 1 and not is_filtered:
                # 如果已经达到了最大行数，就不再尝试补全
                if max_rows is not None and len(unique_rows_y) >= max_rows:
                    pass 
                else:
                    # 计算平均行间距
                    if len(unique_rows_y) >= 2:
                        sorted_rows = sorted(unique_rows_y)
                        gaps = [sorted_rows[i+1] - sorted_rows[i] for i in range(len(sorted_rows)-1)]
                        avg_step_y = sum(gaps) / len(gaps)
                    else:
                        # 如果只有一行，使用传入的 avg_h 作为估算基准 (通常行距 >= 2*h)
                        # 或者无法估算，暂不处理
                        avg_step_y = avg_h * 1.5 

                    # 检查第一行是否偏下
                    # 如果 min_y > avg_step_y * 0.8，说明顶部有空间容纳上一行
                    min_row_y = min(unique_rows_y)
                    if avg_step_y > 10 and min_row_y > avg_step_y * 0.8:
                        missing_y = int(min_row_y - avg_step_y)
                        # 允许稍微越界 (Y<0)，后续会截断
                        # 但不能太离谱
                        if missing_y > -avg_step_y * 0.5:
                            if missing_y < 0: missing_y = 5 # 默认给一个很小的值
                            unique_rows_y.insert(0, missing_y)
                            # print(f"【Fix】推断并补全缺失的顶部行: Y={missing_y}")

            # print(f"全局检测到的行Y坐标: {unique_rows_y}")

            # 2. 按列分组轮廓 (X轴)
            # 使用简单的距离阈值分组
            # 使用左上角X坐标进行聚类，避免宽轮廓导致的中心偏移
            x_positions = [x for (x, y, w, h) in contours]
            x_clusters = []
            x_cluster_threshold = avg_w * 0.8
            
            # 将轮廓分配到列
            # 结构: {col_index: [contour_list, avg_x]}
            cols = {} 
            
            # 先确定列中心
            sorted_x = sorted(x_positions)
            unique_cols_x = []
            for x_c in sorted_x:
                if not unique_cols_x or abs(x_c - unique_cols_x[-1]) > x_cluster_threshold:
                    unique_cols_x.append(x_c)
            
            # 分配轮廓
            for cnt in contours:
                cx = cnt[0]  # 使用左上角X
                # 找最近的列
                best_col_idx = -1
                min_dist = float('inf')
                for idx, col_x in enumerate(unique_cols_x):
                    dist = abs(cx - col_x)
                    if dist < min_dist:
                        min_dist = dist
                        best_col_idx = idx
                
                if min_dist < x_cluster_threshold * 1.5: # 稍微放宽
                    if best_col_idx not in cols:
                        cols[best_col_idx] = []
                    cols[best_col_idx].append(cnt)

            # 3. 检查每一列，补偿缺失的行
            for col_idx, col_contours in cols.items():
                col_y_centers = [y + h/2 for (x, y, w, h) in col_contours]
                avg_col_w = int(sum(c[2] for c in col_contours) / len(col_contours))
                avg_col_h = int(sum(c[3] for c in col_contours) / len(col_contours))
                avg_col_x = int(sum(c[0] for c in col_contours) / len(col_contours)) # 使用左上角X

                for row_y in unique_rows_y:
                    # 检查当前列是否在该行有轮廓
                    has_row = False
                    for y_c in col_y_centers:
                        if abs(y_c - row_y) < cluster_threshold:
                            has_row = True
                            break
                    
                    if not has_row:
                        # 补偿缺失的轮廓
                        # 构造新的轮廓 (x, y, w, h)
                        # 注意 row_y 是中心Y，avg_col_x 是左上角X (这里其实应该是中心X更准，但我们用avg_col_x近似)
                        # 如果 avg_col_x 是左上角平均值，那就直接用
                        
                        comp_y = int(row_y - avg_col_h / 2)
                        comp_x = avg_col_x 
                        
                        compensated_contour = (comp_x, comp_y, avg_col_w, avg_col_h)
                        compensated_contours.append(compensated_contour)
                        compensated_contours_set.add(compensated_contour)
                        # print(f"补偿轮廓(Col {col_idx}): X={comp_x} Y={comp_y}")

        return compensated_contours
    
    # 应用补偿机制
    if layout in ("row", "column"):
        # Calculate max rows (options) for compensation limit
        max_rows_limit = 4
        if options_config:
            max_rows_limit = max(options_config.values())
            
        answer_contours = compensate_missing_options(answer_contours, layout_type=layout, avg_w=avg_w, avg_h=avg_h, max_rows=max_rows_limit, is_filtered=is_column_filtered)
        # print(f"补偿后的轮廓数量: {len(answer_contours)}")

    # 重新按位置排序
    answer_contours.sort(key=lambda cnt: (cnt[1], cnt[0]))

    # 获取图像尺寸
    img_h, img_w = thresh.shape[:2]

    # Define debug_mode safely
    debug_mode = False

    gray_means = {}
    gray_mean_values = []
    for (x, y, w, h) in answer_contours:
        bw = max(2, min(w // 10, h // 10))
        gx1 = max(0, x + bw)
        gy1 = max(0, y + bw)
        gx2 = min(img_w, x + w - bw)
        gy2 = min(img_h, y + h - bw)
        if gx2 > gx1 and gy2 > gy1:
            roi_gray = gray[gy1:gy2, gx1:gx2]
            mean_val = float(np.mean(roi_gray)) if roi_gray.size else 0.0
        else:
            mean_val = 0.0
        gray_means[(x, y, w, h)] = mean_val
        gray_mean_values.append(mean_val)

    gray_mean_threshold = None
    if gray_mean_values:
        gray_std = float(np.std(gray_mean_values))
        if gray_std >= 15:
            means_array = np.array(gray_mean_values, dtype=np.uint8)
            gray_mean_threshold = cv2.threshold(means_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0]
    gray_mean_abs_threshold = 200.0
    if gray_mean_threshold is not None:
        gray_mean_effective_threshold = min(gray_mean_threshold + 10, gray_mean_abs_threshold)
    else:
        gray_mean_effective_threshold = gray_mean_abs_threshold

    for (x, y, w, h) in answer_contours:
        current_row_index = -1
        row_center_y = None
        if layout == "row" and max_bottom > 0 and question_total > 0:
            for i, row_y in enumerate(unique_rows):
                if abs(y - row_y) <= row_threshold:
                    current_row_index = i
                    row_center_y = row_y
                    break

        if layout == "row":
            row_index_for_options = current_row_index if current_row_index >= 0 else int(y // (max_bottom / question_total)) if max_bottom > 0 and question_total > 0 else 0
            question_number_for_options = start_question_num + row_index_for_options
            num_options = options_config.get(question_number_for_options, default_option_count) if options_config else default_option_count
            option_letters = [chr(65 + i) for i in range(num_options)]
            center_x = x + w/2
            if max_right > 0 and num_options > 0:
                section_width = (max_right - min_x) / num_options
                section_index_w = int((center_x - min_x) // section_width)
                if 0 <= section_index_w < num_options:
                    option_letter = option_letters[section_index_w]
                else:
                    option_letter = 'X'
            else:
                section_width = 0
                section_index_w = -1
                option_letter = 'X'
        else:
            current_col_index = -1
            if question_total > 0:
                x_positions = [cx for (cx, cy, cw, ch) in answer_contours]
                avg_w2 = sum([cw for (cx, cy, cw, ch) in answer_contours]) / len(answer_contours) if answer_contours else 20
                col_threshold2 = avg_w2 * 0.8
                unique_cols_local = []
                for x0 in sorted(set(x_positions)):
                    if not unique_cols_local or abs(x0 - unique_cols_local[-1]) > col_threshold2:
                        unique_cols_local.append(x0)
                distances = [(abs(x - col_x), idx) for idx, col_x in enumerate(unique_cols_local)]
                if distances:
                    current_col_index = min(distances)[1]

            question_number_for_options = start_question_num + (current_col_index if current_col_index >= 0 else 0)
            num_options = options_config.get(question_number_for_options, default_option_count) if options_config else default_option_count
            option_letters = [chr(65 + i) for i in range(num_options)]

            center_y = y + h/2
            if (max_bottom - min_y) > 0 and num_options > 0:
                section_height = (max_bottom - min_y) / num_options
                section_index_h = int((center_y - min_y) // section_height)
                if 0 <= section_index_h < num_options:
                    option_letter = option_letters[section_index_h]
                else:
                    option_letter = 'X'
            else:
                option_letter = 'X'

        roi_x, roi_y, roi_w, roi_h = x, y, w, h
        if layout == "row" and section_width > 0 and num_options > 0 and current_row_index >= 0 and avg_w > 0 and avg_h > 0:
            if w < avg_w * 0.7 or h < avg_h * 0.7:
                slot_center_x = min_x + (section_index_w + 0.5) * section_width if 0 <= section_index_w < num_options else x + w / 2
                roi_w = int(section_width * 0.9)
                roi_h = int(avg_h)
                roi_x = int(slot_center_x - roi_w / 2)
                roi_y = int(row_center_y - roi_h / 2)
                roi_x = max(0, min(roi_x, img_w - roi_w))
                roi_y = max(0, min(roi_y, img_h - roi_h))
                roi_w = min(roi_w, img_w - roi_x)
                roi_h = min(roi_h, img_h - roi_y)

        option_roi = thresh[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]
        
        if debug_mode:
             print(f"Checking contour at {x},{y} w={w} h={h}")

        edge_letters = {option_letters[0], option_letters[-1]} if option_letters else set()
        is_edge_option = option_letter in edge_letters
        filled = detect_rectangle_filling(option_roi, debug=debug_mode, is_top_edge=is_edge_option, is_bottom_edge=is_edge_option)
        if filled and gray_mean_effective_threshold is not None:
            inner_mean = gray_means.get((x, y, w, h))
            if inner_mean is not None and inner_mean > gray_mean_effective_threshold:
                filled = False
        
        is_compensated = (x, y, w, h) in compensated_contours_set

        if filled:
            color = (0, 255, 0)
            thickness = 4
            cv2.rectangle(result_img, (x-2, y-2), (x + w+2, y + h+2), (0, 255, 255), 2)
        else:
            color = (0, 0, 255)
            thickness = 2
        
        cv2.rectangle(result_img, (x, y), (x + w, y + h), color, thickness)
        #option_letter = chr(65 + len(options) % 4)
        cv2.putText(result_img, option_letter,
                    (x + 5, y + 15), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 0, 0), 2)
        
        # 添加填涂状态标记
        status_text = "FILLED" if filled else "EMPTY"
        status_color = (0, 255, 0) if filled else (0, 0, 255)
        cv2.putText(result_img, status_text,
                    (x + 5, y + h - 5), cv2.FONT_HERSHEY_SIMPLEX,
                    0.3, status_color, 1)

        options.append((x, filled))

        # 计算题目编号（按布局分支）
        if layout == "row":
            if current_row_index >= 0:
                question_number = start_question_num + current_row_index
            else:
                question_number = 'Y'
        else:
            # 一列一题：按列索引计算题号
            if question_total > 0:
                # 复用上面计算的 current_col_index（若不可用则重新计算）
                if 'current_col_index' in locals() and current_col_index is not None and current_col_index >= 0:
                    question_number = start_question_num + current_col_index
                else:
                    # 后备：根据x定位最近列中心
                    x_positions = [cx for (cx, cy, cw, ch) in answer_contours]
                    avg_w2 = sum([cw for (cx, cy, cw, ch) in answer_contours]) / len(answer_contours) if answer_contours else 20
                    col_threshold2 = avg_w2 * 0.8
                    unique_cols_local = []
                    for x0 in sorted(set(x_positions)):
                        if not unique_cols_local or abs(x0 - unique_cols_local[-1]) > col_threshold2:
                            unique_cols_local.append(x0)
                    distances = [(abs(x - col_x), idx) for idx, col_x in enumerate(unique_cols_local)]
                    if distances:
                        question_number = start_question_num + min(distances)[1]
                    else:
                        question_number = 'X'
            else:
                question_number = 'X'

        # 存储选项信息
        if question_number not in question_options:
            question_options[question_number] = []
        
        area_value = roi_w * roi_h
        question_options[question_number].append({
            'option': option_letter,
            'filled': filled,
            'position': (x, y),
            'size': (w, h),
            'area': area_value
        })

    # 【Fix】确保每道题都包含所有预期选项 (A, B, C, D...)
    # 如果某个选项因检测失败或被遮罩过滤而缺失，补全为“未填涂”
    for q_num in list(question_options.keys()):
        if q_num == 'X' or q_num == 'Y': continue
        
        # 获取该题预期选项数
        expected_count = options_config.get(q_num, default_option_count) if options_config else default_option_count
        expected_letters = [chr(65 + i) for i in range(expected_count)]
        
        existing_letters = {opt['option'] for opt in question_options[q_num]}
        
        size_candidates = [opt.get('size') for opt in question_options[q_num] if isinstance(opt.get('size'), tuple) and opt.get('size')[0] > 0 and opt.get('size')[1] > 0]
        if size_candidates:
            avg_w_q = int(np.median([s[0] for s in size_candidates]))
            avg_h_q = int(np.median([s[1] for s in size_candidates]))
        else:
            avg_w_q = int(avg_w) if avg_w else 20
            avg_h_q = int(avg_h) if avg_h else 20

        center_candidates = []
        for opt in question_options[q_num]:
            if isinstance(opt.get('position'), tuple) and isinstance(opt.get('size'), tuple):
                ox, oy = opt['position']
                ow, oh = opt['size']
                if ow > 0 and oh > 0:
                    center_candidates.append((ox + ow / 2.0, oy + oh / 2.0))

        row_center_est = None
        col_center_est = None
        if center_candidates:
            row_center_est = float(np.median([c[1] for c in center_candidates]))
            col_center_est = float(np.median([c[0] for c in center_candidates]))

        for letter in expected_letters:
            if letter not in existing_letters:
                letter_index = ord(letter) - 65
                if layout == "row":
                    section_width = (max_right - min_x) / expected_count if max_right > min_x and expected_count > 0 else 0
                    if row_center_est is None:
                        row_index = q_num - start_question_num
                        if isinstance(row_index, int) and row_index >= 0 and 'unique_rows' in locals() and row_index < len(unique_rows):
                            row_center_est = float(unique_rows[row_index])
                        elif max_bottom > min_y and question_total > 0:
                            row_center_est = float(min_y + (row_index + 0.5) * ((max_bottom - min_y) / float(question_total)))
                        else:
                            row_center_est = float(min_y + avg_h_q / 2.0)
                    if section_width > 0:
                        center_x = float(min_x + (letter_index + 0.5) * section_width)
                    else:
                        center_x = float(min_x + (letter_index + 0.5) * avg_w_q)
                    center_y = row_center_est
                else:
                    section_height = (max_bottom - min_y) / expected_count if max_bottom > min_y and expected_count > 0 else 0
                    if col_center_est is None:
                        col_index = q_num - start_question_num
                        if isinstance(col_index, int) and col_index >= 0 and 'unique_cols' in locals() and col_index < len(unique_cols):
                            col_center_est = float(unique_cols[col_index] + avg_w_q / 2.0)
                        else:
                            col_center_est = float(min_x + avg_w_q / 2.0)
                    if section_height > 0:
                        center_y = float(min_y + (letter_index + 0.5) * section_height)
                    else:
                        center_y = float(min_y + (letter_index + 0.5) * avg_h_q)
                    center_x = col_center_est

                vx = int(center_x - avg_w_q / 2.0)
                vy = int(center_y - avg_h_q / 2.0)
                vx = max(0, min(vx, img_w - avg_w_q))
                vy = max(0, min(vy, img_h - avg_h_q))

                option_roi = thresh[vy:vy + avg_h_q, vx:vx + avg_w_q]
                edge_letters = {expected_letters[0], expected_letters[-1]} if expected_letters else set()
                is_edge_option = letter in edge_letters
                filled_virtual = detect_rectangle_filling(option_roi, debug=debug_mode, is_top_edge=is_edge_option, is_bottom_edge=is_edge_option)
                if filled_virtual and gray_mean_effective_threshold is not None:
                    bw = max(2, min(avg_w_q // 10, avg_h_q // 10))
                    gx1 = max(0, vx + bw)
                    gy1 = max(0, vy + bw)
                    gx2 = min(img_w, vx + avg_w_q - bw)
                    gy2 = min(img_h, vy + avg_h_q - bw)
                    if gx2 > gx1 and gy2 > gy1:
                        roi_gray = gray[gy1:gy2, gx1:gx2]
                        inner_mean = float(np.mean(roi_gray)) if roi_gray.size else 0.0
                        if inner_mean > gray_mean_effective_threshold:
                            filled_virtual = False

                virtual_opt = {
                    'option': letter,
                    'filled': filled_virtual,
                    'position': (vx, vy),
                    'size': (avg_w_q, avg_h_q),
                    'area': avg_w_q * avg_h_q if filled_virtual else 0,
                    'is_virtual': True
                }
                question_options[q_num].append(virtual_opt)
        
        # 按字母排序
        question_options[q_num].sort(key=lambda x: x['option'])

    # 面积过滤工具：根据最大面积与次大面积的差距进行筛选
    def _filter_by_area_gap(filled_opts, keep_ratio=area_keep_ratio, gap_factor=area_gap_factor):
        if not filled_opts:
            return []
        if len(filled_opts) == 1:
            return filled_opts

        # 按面积降序排列
        sorted_opts = sorted(filled_opts, key=lambda x: x['area'], reverse=True)
        largest = sorted_opts[0]
        second = sorted_opts[1]

        # 如果最大远大于次大（倍数>=gap_factor），直接只保留最大，视为明显差距过大
        if second['area'] > 0 and (largest['area'] / second['area']) >= gap_factor:
            return [largest]

        # 否则保留与最大面积接近的选项（>= keep_ratio * 最大面积）
        threshold = largest['area'] * keep_ratio
        kept = [opt for opt in sorted_opts if opt['area'] >= threshold]
        return kept if kept else [largest]

    # 处理每个题目的答案
    for question_num, options_list in question_options.items():
        if isinstance(question_num, int):
            # 获取题目类型（默认为单选题）
            question_type = question_types.get(question_num, 'single')
            
            # 获取所有填涂的选项 (排除无效列 'X')
            filled_options = [opt for opt in options_list if opt['filled'] and opt['option'] != 'X']
            
            if not filled_options:
                if question_type == 'multiple':
                    results[question_num] = []
                else:
                    results[question_num] = ""
                continue

            expected_cnt = options_config.get(question_num, default_option_count) if options_config else default_option_count
            all_areas_desc = sorted([opt['area'] for opt in options_list], reverse=True)
            if len(all_areas_desc) >= 1:
                ref_slice = all_areas_desc[:max(1, min(expected_cnt, len(all_areas_desc)))]
                reference_area = float(np.median(ref_slice))
            else:
                reference_area = 0.0

            MIN_ABS_REF_AREA = 300.0 
            if reference_area < MIN_ABS_REF_AREA:
                reference_area = MIN_ABS_REF_AREA

            valid_area_threshold = reference_area * float(min_valid_ratio)
            edge_letters = {chr(65), chr(65 + expected_cnt - 1)} if expected_cnt > 0 else {chr(65)}
            relaxed_threshold = valid_area_threshold * 0.3
            pre_filtered = []
            for opt in filled_options:
                if opt['area'] >= valid_area_threshold:
                    pre_filtered.append(opt)
                    continue
                if opt['option'] in edge_letters and opt['area'] >= relaxed_threshold:
                    pre_filtered.append(opt)

            if not pre_filtered:
                if question_type == 'multiple':
                    results[question_num] = []
                else:
                    results[question_num] = ""
                if filled_options:
                     print(f"DEBUG_FILTER: Q{question_num} filled options rejected by area threshold.")
                     print(f"              Reference Area (Median of top {len(ref_slice)}): {reference_area}")
                     print(f"              Threshold (x{min_valid_ratio}): {valid_area_threshold}")
                     for opt in filled_options:
                         print(f"              REJECTED Opt {opt['option']}: Area {opt['area']}")
                continue

            if question_type == 'multiple':
                filtered = pre_filtered
            else:
                filtered = _filter_by_area_gap(pre_filtered)
            filtered_sorted = sorted(filtered, key=lambda x: x['area'], reverse=True)
            ratio_threshold = 2.5
            multi_candidate = False
            if len(filtered_sorted) >= 2 and filtered_sorted[1]['area'] > 0:
                if (filtered_sorted[0]['area'] / filtered_sorted[1]['area']) < ratio_threshold:
                    multi_candidate = True
            if multi_candidate and question_type != 'multiple':
                filtered_sorted = sorted(pre_filtered, key=lambda x: x['area'], reverse=True)

            if question_type == 'multiple' or multi_candidate:
                unique_letters = sorted({opt['option'] for opt in filtered_sorted})
                results[question_num] = unique_letters
            else:
                if len(filtered_sorted) > 1:
                    print(f"警告：题目 {question_num} 检测到多个填涂选项（面积相近），选择面积最大的")
                    for opt in filtered_sorted:
                        print(f"  选项 {opt['option']}: 面积={opt['area']}")
                largest_option = filtered_sorted[0]
                results[question_num] = largest_option['option']

            # 同步详细选项的填涂状态与最终识别结果
            # 确保单选题只保留最终选定的那个选项为填涂状态，避免多余的绿色框
            final_ans = results.get(question_num, "")
            accepted_opts = set()
            if isinstance(final_ans, list):
                accepted_opts = set(final_ans)
            elif isinstance(final_ans, str) and final_ans:
                accepted_opts = set(list(final_ans))
            
            for opt in options_list:
                opt['filled'] = opt['option'] in accepted_opts
                if opt.get('is_virtual'):
                    ox, oy = opt['position']
                    ow, oh = opt.get('size', (0, 0))
                    if ow > 0 and oh > 0:
                        color = (0, 255, 0) if opt['filled'] else (0, 0, 255)
                        thickness = 2
                        cv2.rectangle(result_img, (ox, oy), (ox + ow, oy + oh), color, thickness)
                        cv2.putText(result_img, opt['option'],
                                    (ox + 5, oy + 15), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.5, (255, 0, 0), 2)
                        status_text = "FILLED" if opt['filled'] else "EMPTY"
                        status_color = (0, 255, 0) if opt['filled'] else (0, 0, 255)
                        cv2.putText(result_img, status_text,
                                    (ox + 5, oy + oh - 5), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.3, status_color, 1)

    # 计算全局坐标映射
    if global_box:
        # global_box is (cx, cy, w, h) normalized relative to original image
        gcx, gcy, gw, gh = global_box
        g_left = gcx - gw/2
        g_top = gcy - gh/2
        
        # Current image dimensions
        curr_h, curr_w = image.shape[:2]
        
        for q_num, opts in question_options.items():
            for opt in opts:
                lx, ly = opt['position']
                lw, lh = opt.get('size', (0, 0))
                
                if curr_w > 0 and curr_h > 0:
                    # Normalize local coordinates relative to the crop
                    norm_lx = lx / curr_w
                    norm_ly = ly / curr_h
                    norm_lw = lw / curr_w
                    norm_lh = lh / curr_h
                    
                    # Map to global normalized coordinates
                    # Global X = Crop Left + Local Normalized X * Crop Width
                    gl_x = g_left + norm_lx * gw
                    gl_y = g_top + norm_ly * gh
                    gl_w = norm_lw * gw
                    gl_h = norm_lh * gh
                    
                    opt['global_position'] = (gl_x, gl_y, gl_w, gl_h)
                else:
                    opt['global_position'] = None

    # 显示最终结果和调试信息
    print("\n=== 最终识别结果 ===")
    for question_num, answer in results.items():
        print(f"题目 {question_num}: {answer}")
    
    print("\n=== 详细选项信息 ===")
    for question_num, options_list in question_options.items():
        if isinstance(question_num, int):
            print(f"题目 {question_num}:")
            for opt in options_list:
                status = "已填涂" if opt['filled'] else "未填涂"
                print(f"  选项 {opt['option']}: {status} (位置: {opt['position']}, 面积: {opt['area']})")
    
    # cv2.imshow("07. Final Result", result_img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    return results, question_options


def rename_images(folder_path):
    # 定义支持的图片扩展名
    image_exts = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

    # 获取文件夹下所有图片文件（按文件名排序）
    image_files = sorted(
        [f for f in os.listdir(folder_path) if f.lower().endswith(image_exts)],
        key=lambda x: os.path.splitext(x)[0]  # 按文件名排序（忽略扩展名）
    )

    # 遍历并重命名
    for idx, filename in enumerate(image_files, 1):
        src_path = os.path.join(folder_path, filename)
        new_name = f"answer_{idx}.jpg"  # 统一保存为 .jpg 格式
        dst_path = os.path.join(folder_path, new_name)

        # 避免覆盖已存在的文件（如果目标文件名存在，先删除）
        if os.path.exists(dst_path):
            os.remove(dst_path)

        os.rename(src_path, dst_path)
        print(f"Renamed: {filename} -> {new_name}")


def extract_sequence(filename):
    """提取文件名中的逻辑序号"""
    if filename == "sheet.jpg":
        return 1
    num_part = re.search(r'sheet(\d+)\.jpg', filename).group(1)
    # suffix = num_part[3:]  # 去掉前缀"104"
    # return int(suffix)
    return int(num_part)


def get_sorted_files(folder_path, mode):
    """获取按模式排序的文件列表"""
    files = []
    for f in os.listdir(folder_path):
        if f.lower().endswith(".jpg"):
            try:
                seq = extract_sequence(f)
                files.append((seq, f))
            except:
                continue

    # 按序号排序获取所有文件
    sorted_files = [f for _, f in sorted(files, key=lambda x: x[0])]
    
    if mode == "A":
        # A模式：行优先排序（自然顺序）
        # 直接按序号顺序排列：1,2,3,4,5,6,7,8...
        print(f"A模式行优先排序: 按自然顺序 {sorted_files[:8] if len(sorted_files) >= 8 else sorted_files}")
        return sorted_files

    elif mode == "B":
        # B模式：固定的列优先顺序（保持原有逻辑）
        b_order = [1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15, 4, 8, 12, 16]
        seq_map = {seq: f for seq, f in files}
        ordered_files = [seq_map[seq] for seq in b_order if seq in seq_map]
        print(f"B模式固定排序: {ordered_files}")
        return ordered_files
    
    # 默认返回自然顺序
    return sorted_files

def get_question_number_mapping(question_types, group_size: int, num_files: int, start_number: int = 1):
    """
    根据题目类型配置与题组数量生成题号映射
    
    参数:
        question_types: 题目类型配置字典
        group_size: 每张图片包含的题目数量
        num_files: 图片文件数量
        start_number: 起始题号（默认1）
    
    返回:
        list: 每张图片对应的起始题号列表（长度为 num_files）
    """
    try:
        g = int(group_size)
    except Exception:
        g = 5
    if g < 1:
        g = 1

    # 无题型配置：按组大小顺序递增
    if not question_types:
        return [start_number + i * g for i in range(num_files)]

    # 有题型配置：按题号排序后，每组取第一个作为起始题号
    question_numbers = sorted(question_types.keys())
    mapping = [question_numbers[i] for i in range(0, len(question_numbers), g)]
    # 截断或补齐到与图片数量一致
    if len(mapping) >= num_files:
        return mapping[:num_files]
    else:
        tail_start = mapping[-1] if mapping else start_number
        extra = [tail_start + (i + 1) * g for i in range(num_files - len(mapping))]
        return mapping + extra

def recognize_answer_main(mode="B", question_types_file=None, start_number=1, answer_config_file=None, layout: str = "row", group_size: int = 5):
    """
    主答案识别函数，支持多选题和动态选项数量
    
    参数:
        mode: 识别模式，"A"为行优先排序（自然顺序），"B"为固定列优先排序
        question_types_file: 题目类型配置文件路径（可选）
        start_number: 起始题号（默认为1）
        answer_config_file: 答案配置文件路径（可选，用于获取选项数量配置）
    """
    # 加载题目类型配置
    question_types = {}
    options_config = {}
    
    # 1. 优先从答案配置文件加载，并自动推断题目类型
    if answer_config_file and os.path.exists(answer_config_file):
        try:
            # 获取答案配置和选项数量配置
            answers_config, _, options_config = parse_multiple_choice_answers(answer_config_file)
            print(f"已加载选项数量配置: {len(options_config)} 个题目")
            
            # 根据答案配置自动推断题目类型
            # 规则：答案为列表或长度>1的字符串 -> 多选题，否则 -> 单选题
            for q_num, ans in answers_config.items():
                if isinstance(ans, list) or (isinstance(ans, str) and len(ans) > 1 and ans.isalpha()):
                    question_types[q_num] = 'multiple'
                else:
                    question_types[q_num] = 'single'
            
            print(f"根据答案配置自动推断题目类型:")
            single_count = sum(1 for t in question_types.values() if t == 'single')
            multiple_count = sum(1 for t in question_types.values() if t == 'multiple')
            print(f"  单选题: {single_count} 个")
            print(f"  多选题: {multiple_count} 个")
            
            # 显示题号范围
            if question_types:
                question_numbers = sorted(question_types.keys())
                print(f"  题号范围: {min(question_numbers)}-{max(question_numbers)}")

        except Exception as e:
            print(f"加载答案配置文件失败: {e}")
            print("将使用默认配置（所有题目为4个选项）")

    # 2. 如果没有成功推断（例如没提供答案文件），尝试加载旧的题目类型文件（兼容性保留）
    if not question_types and question_types_file and os.path.exists(question_types_file):
        try:
            # 使用新的题目类型解析器
            question_types = parse_question_types(question_types_file)
            print(f"已加载题目类型配置(旧方式): {len(question_types)} 个题目")
            
            # 显示配置详情
            single_count = sum(1 for t in question_types.values() if t == 'single')
            multiple_count = sum(1 for t in question_types.values() if t == 'multiple')
            print(f"  单选题: {single_count} 个")
            print(f"  多选题: {multiple_count} 个")
            
        except Exception as e:
            print(f"加载题目类型配置文件失败: {e}")
            print("将使用默认配置（所有题目为单选题）")

    if (not answer_config_file or not os.path.exists(answer_config_file)) and os.path.exists(os.path.join(project_root, "config", "answer_config", "answer_multiple.txt")):
        if not question_types or all(t == 'single' for t in question_types.values()):
            try:
                fallback_path = os.path.join(project_root, "config", "answer_config", "answer_multiple.txt")
                answers_config, _, options_config = parse_multiple_choice_answers(fallback_path)
                if answers_config:
                    question_types = {}
                    for q_num, ans in answers_config.items():
                        if isinstance(ans, list) or (isinstance(ans, str) and len(ans) > 1 and ans.isalpha()):
                            question_types[q_num] = 'multiple'
                        else:
                            question_types[q_num] = 'single'
                    print(f"根据默认答案配置自动推断题目类型: {len(question_types)} 个题目")
                    single_count = sum(1 for t in question_types.values() if t == 'single')
                    multiple_count = sum(1 for t in question_types.values() if t == 'multiple')
                    print(f"  单选题: {single_count} 个")
                    print(f"  多选题: {multiple_count} 个")
            except Exception as e:
                print(f"加载默认答案配置失败: {e}")
    
    if not question_types:
        print("未获取到题目类型配置，默认所有题目为单选题")
    
    # 获取answerArea文件夹下的所有图片
    # 优先使用YOLOv5检测结果路径，如果不存在则使用当前目录下的answerArea
    yolo_answer_path = os.path.join("runs", "detect", "exp", "crops", "answerArea")
    current_answer_path = "answerArea"
    
    if os.path.exists(yolo_answer_path):
        answer_area_path = yolo_answer_path
        print(f"使用YOLOv5检测结果路径: {answer_area_path}")
    elif os.path.exists(current_answer_path):
        answer_area_path = current_answer_path
        print(f"使用当前目录answerArea路径: {answer_area_path}")
    else:
        print(f"错误：找不到答题卡文件夹")
        print(f"请确保以下路径之一存在：")
        print(f"  1. {yolo_answer_path} (YOLOv5检测结果)")
        print(f"  2. {current_answer_path} (当前目录)")
        return
    if not os.path.exists(answer_area_path):
        print(f"错误：找不到文件夹 {answer_area_path}")
        return
    
    # 获取排序后的文件列表
    sorted_files = get_sorted_files(answer_area_path, mode)
    
    if not sorted_files:
        print(f"错误：在 {answer_area_path} 文件夹中没有找到图片文件")
        return
    
    print(f"使用{mode}模式，找到 {len(sorted_files)} 个图片文件")
    
    # 根据题目类型配置与题组数量生成题号映射
    question_mapping = get_question_number_mapping(question_types, group_size, len(sorted_files), start_number)
    print(f"\n题号映射: {question_mapping}")
    
    # 存储所有识别结果
    all_results = {}
    all_detailed_results = {}

    # 尝试加载YOLO标签以进行坐标映射
    label_path = os.path.join(os.path.dirname(os.path.dirname(answer_area_path)), "labels", "sheet.txt")
    class_boxes_map = {}  # class_id -> list of boxes
    target_class_boxes = []
    
    if os.path.exists(label_path):
        try:
            with open(label_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        cls_id = int(parts[0])
                        # x, y, w, h (normalized)
                        box = list(map(float, parts[1:5]))
                        if cls_id not in class_boxes_map:
                            class_boxes_map[cls_id] = []
                        class_boxes_map[cls_id].append(box)
            
            # 尝试匹配标签类与裁剪图片
            # 策略：寻找数量与图片数量一致的类，或者如果只有一个类则直接使用
            candidates = [k for k, v in class_boxes_map.items() if len(v) == len(sorted_files)]
            if len(candidates) == 1:
                target_class_boxes = class_boxes_map[candidates[0]]
                print(f"成功匹配标签类 {candidates[0]}，共 {len(target_class_boxes)} 个目标")
            elif len(class_boxes_map) == 1:
                cls_id = list(class_boxes_map.keys())[0]
                target_class_boxes = class_boxes_map[cls_id]
                print(f"使用唯一检测类 {cls_id} 的标签，共 {len(target_class_boxes)} 个目标")
            else:
                print(f"警告: 无法精确匹配标签与裁剪图。文件数: {len(sorted_files)}, 标签分布: {{k:len(v) for k,v in class_boxes_map.items()}}")
                # 如果没有精确匹配，但有且仅有一个类别的数量大于等于文件数，尝试使用它
                # (可能是误检多了几个，但顺序是对的)
                possible_classes = [k for k, v in class_boxes_map.items() if len(v) >= len(sorted_files)]
                if len(possible_classes) == 1:
                     target_class_boxes = class_boxes_map[possible_classes[0]]
                     print(f"使用最接近的标签类 {possible_classes[0]}，共 {len(target_class_boxes)} 个目标")
                
        except Exception as e:
            print(f"警告: 加载标签文件失败: {e}")

    # 逐个处理图片
    for i, filename in enumerate(sorted_files):
        file_path = os.path.join(answer_area_path, filename)
        print(f"\n正在处理第 {i+1} 个文件: {filename}")
        
        try:
            # 根据映射获取当前文件的起始题号
            if i < len(question_mapping):
                start_question_num = question_mapping[i]
            else:
                print(f"警告: 图片数量超出配置范围，跳过文件 {filename}")
                continue
            
            # 识别答题卡
            print(f"\n正在识别第 {i+1} 张答题卡: {filename}")
            print(f"起始题号: {start_question_num}")

            # 获取对应的全局坐标框
            global_box = None
            if target_class_boxes:
                # 通过文件名中的序号匹配 YOLO 标签
                # extract_sequence 返回 1, 2, 3... 对应 target_class_boxes 的 index 0, 1, 2...
                try:
                    seq = extract_sequence(filename)
                    if 1 <= seq <= len(target_class_boxes):
                        global_box = target_class_boxes[seq - 1]
                        # print(f"  匹配到全局坐标: {global_box}")
                    else:
                        print(f"  警告: 文件序号 {seq} 超出标签数量 {len(target_class_boxes)}")
                except Exception as e:
                    print(f"  警告: 无法提取文件序号，无法匹配坐标: {e}")
            
            result, detailed_info = recognize_answer_sheet(
                file_path,
                question_types=question_types,
                options_config=options_config,
                start_question_num=start_question_num,
                layout=layout,
                global_box=global_box
            )
            
            # 过滤结果：只保留本图片对应的题号范围，处理最后一组非满组的情况
            # 依据当与围；最后一张用配置最大题号或 group_size 兜底
            filtered_result = {}
            next_start = question_mapping[i+1] if (i + 1) < len(question_mapping) else None

            if question_types:
                configured_numbers = sorted(question_types.keys())
                if next_start:
                    allowed_set = {q for q in configured_numbers if start_question_num <= q < next_start}
                else:
                    # 最后一组：允许从当前起始题号到配置中的最大题号
                    allowed_set = {q for q in configured_numbers if q >= start_question_num}

                for question_num, answer in result.items():
                    if isinstance(question_num, int) and question_num in allowed_set:
                        filtered_result[question_num] = answer
                    else:
                        # 打印被剔除的题号（越界或未配置）
                        if isinstance(question_num, int):
                            print(f"过滤掉非本组题号或未配置题号: {question_num}")
                        else:
                            print(f"过滤掉无效题号标记: {question_num}")
            else:
                # 无题型配置时，按组大小限制，避免越界到下一组
                allowed_range_end = start_question_num + int(group_size) - 1
                for question_num, answer in result.items():
                    if isinstance(question_num, int) and start_question_num <= question_num <= allowed_range_end:
                        filtered_result[question_num] = answer
                    else:
                        if isinstance(question_num, int):
                            print(f"过滤掉越界题号（无配置模式）: {question_num}")
                        else:
                            print(f"过滤掉无效题号标记: {question_num}")
            
            all_results[filename] = filtered_result
            all_detailed_results[filename] = detailed_info
            
            # 打印识别结果
            print(f"识别结果:")
            for question_num in sorted(filtered_result.keys()):
                answer = filtered_result[question_num]
                if isinstance(answer, list):
                    if answer:
                        print(f"  题目 {question_num} (多选): {','.join(answer)}")
                    else:
                        print(f"  题目 {question_num} (多选): 未填涂")
                else:
                    if answer:
                        print(f"  题目 {question_num} (单选): {answer}")
                    else:
                        print(f"  题目 {question_num} (单选): 未填涂")
                        
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")
            continue
    
    # 打印汇总结果
    print(f"\n=== 所有文件识别结果汇总 ===")
    for filename, result in all_results.items():
        print(f"\n文件: {filename}")
        for question_num in sorted(result.keys()):
            answer = result[question_num]
            if isinstance(answer, list):
                if answer:
                    print(f"  题目 {question_num} (多选): {','.join(answer)}")
                else:
                    print(f"  题目 {question_num} (多选): 未填涂")
            else:
                if answer:
                    print(f"  题目 {question_num} (单选): {answer}")
                else:
                    print(f"  题目 {question_num} (单选): 未填涂")
    
    return all_results, all_detailed_results

# 使用示例
if __name__ == "__main__":
    print("请在 test_script 目录下运行测试脚本")
