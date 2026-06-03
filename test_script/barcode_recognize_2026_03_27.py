import os
import sys
import cv2

RUN_DATE = "2026-03-27"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_IMAGE_PATH = r"E:\code_space\code_python\GraderFlow\test_img\answer_185.jpg"


def decode_with_opencv_barcode(image):
    if not hasattr(cv2, "barcode_BarcodeDetector"):
        return []
    detector = cv2.barcode_BarcodeDetector()
    results = []
    decoded_info = []
    decoded_type = []
    ret = detector.detectAndDecode(image)
    if isinstance(ret, tuple):
        if len(ret) == 4:
            ok, decoded_info, decoded_type, _ = ret
            if not ok:
                decoded_info = []
        elif len(ret) == 3:
            decoded_info, decoded_type, _ = ret
    if decoded_info:
        for idx, text in enumerate(decoded_info):
            if text and str(text).strip():
                barcode_type = str(decoded_type[idx]) if decoded_type is not None and idx < len(decoded_type) else ""
                results.append({"method": "opencv_barcode", "text": str(text).strip(), "type": barcode_type})
    if not results and hasattr(detector, "detectAndDecodeMulti"):
        ret_multi = detector.detectAndDecodeMulti(image)
        if isinstance(ret_multi, tuple) and len(ret_multi) >= 2:
            ok_multi = bool(ret_multi[0])
            multi_info = ret_multi[1] if len(ret_multi) > 1 else []
            if ok_multi and multi_info is not None:
                for text in multi_info:
                    if text and str(text).strip():
                        results.append({"method": "opencv_barcode_multi", "text": str(text).strip(), "type": ""})
    return results


def decode_with_pyzbar(image):
    try:
        from pyzbar.pyzbar import decode
    except Exception:
        return []
    decoded = decode(image)
    results = []
    for item in decoded:
        text = item.data.decode("utf-8", errors="ignore")
        if text:
            results.append({
                "method": "pyzbar",
                "text": text,
                "type": str(item.type),
            })
    return results


def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE_PATH
    print(f"RUN_DATE={RUN_DATE}")
    print(f"IMAGE={image_path}")
    if not os.path.exists(image_path):
        print("❌ 图片不存在")
        return 1
    image = cv2.imread(image_path)
    if image is None:
        print("❌ 图片加载失败")
        return 1

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 5)
    enlarged = cv2.resize(image, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
    candidates = [image, gray, binary, enlarged]
    all_results = []
    for candidate in candidates:
        all_results.extend(decode_with_opencv_barcode(candidate))
        all_results.extend(decode_with_pyzbar(candidate))

    unique = []
    seen = set()
    for result in all_results:
        key = (result["text"], result["type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)

    if not unique:
        print("⚠️ 未识别到条形码")
        print("提示：可尝试安装 pyzbar 或使用包含 barcode 模块的 OpenCV 版本")
        return 0

    print(f"✅ 识别到 {len(unique)} 个条形码")
    for idx, result in enumerate(unique, start=1):
        print(f"{idx}. method={result['method']} type={result['type']} text={result['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
