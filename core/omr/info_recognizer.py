from PIL import Image
import argparse
import requests
import json
import base64  # 添加这行
#from paddleocr import PaddleOCR  # 导入 PaddleOCR 模型
# 初始化 PaddleOCR 模型，使用角度分类器，设置语言为中文

#ocr = PaddleOCR(use_angle_cls=True, lang='ch')

def get_access_token():
    """
    使用 API Key，Secret Key 获取access_token，替换下列示例中的应用API Key、应用Secret Key
    """
    client_id = "jMISUOVA869j2XmDLRrWbWEY"  # 将 client_id 设置为变量
    client_secret = "dZj0dMyW2xb4ZUBw2HcQ3qwfFwJbwefJ"  # 如果需要，也可以将 client_secret 设置为变量

    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"

    payload = json.dumps("")
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get("access_token")

def baidu_ocr(image_path):
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
    with open(image_path, 'rb') as f:
        img = base64.b64encode(f.read())
    params = {
        "image": img,
        "language_type": "CHN_ENG",
        "detect_direction": "true"
    }
    access_token = get_access_token()  # 复用您已有的token获取函数
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(f"{url}?access_token={access_token}", data=params, headers=headers)
    print(response.json())
    # result = "\n".join([i['words'] for i in response.json().get('words_result', [])])
    data = response.json()
    print(data)

    # 提取words字段生成列表
    words_list = [item["words"] for item in data["words_result"]]

    print(words_list)  # 输出: ['陈广南', '03005']
    return words_list

def crop_image(input_path, output_path):
    try:
        # 打开原始图片
        with Image.open(input_path) as img:
            width, height = img.size

            # 计算截取区域尺寸
            crop_width = width // 3
            crop_height = height // 5

            print(crop_height)
            print(crop_width)

            # 检查截取尺寸有效性
            if crop_width == 0 or crop_height == 0:
                raise ValueError("图片尺寸过小，无法截取指定比例区域")

            # 定义截取区域 (左, 上, 右, 下)
            crop_area = (320, 320, crop_width, crop_height)

            # 执行截取操作
            cropped_img = img.crop(crop_area)

            # 保存结果
            cropped_img.save(output_path)
            print(f"截图成功！保存至: {output_path}")
            print(f"截取尺寸: {crop_width}x{crop_height} 像素")

    except FileNotFoundError:
        print(f"错误：输入文件 '{input_path}' 不存在")
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")

def recognize_name():
    # 定义主观题识别函数
    # img = cv2.imread('subjective_area.jpg')  # 读取主观题区域的图像
    crop_image("undet_img/sheet.jpg", "output.jpg")
    img_path = 'output.jpg'  # 设置主观题区域图像路径
    #result = ocr.ocr(img_path, cls=True)  # 使用OCR进行图像识别
    result = baidu_ocr(img_path)
    return result
    # txts = []  # 用于存储识别到的文本
    # for line in result:  # 遍历识别结果中的每一行
    #     for word_info in line:  # 遍历每行中的每个单词信息
    #         txts.append(word_info[1][0])  # 提取每个单词的文本部分并添加到列表中
    # print(txts)
    # return txts
    #final_result = ''.join(txts)  # 将识别到的文本连接成一个字符串
if __name__ == "__main__":
    # input_path = r"E:\code_space\code_python\VQD\AnsweringSystem\test_img\answer_104.jpg"
    # output_path = r"E:\code_space\code_python\VQD\AnsweringSystem\output.jpg"
    # # 执行截取操作
    # crop_image(input_path, output_path)
    recognize_name()
