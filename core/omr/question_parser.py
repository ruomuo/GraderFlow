import os

def parse_question_types(file_path):
    """
    解析题目类型配置文件
    
    参数:
        file_path: 配置文件路径
    
    返回:
        dict: 题目类型字典，格式为 {题号: 'single'/'multiple'}
    """
    question_types = {}
    
    if not os.path.exists(file_path):
        print(f"题目类型配置文件不存在: {file_path}")
        return question_types
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳过空行和注释行
                if not line or line.startswith('#'):
                    continue
                
                # 解析配置行
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) == 2:
                        question_range = parts[0].strip()
                        question_type = parts[1].strip().lower()
                        
                        if question_type not in ['single', 'multiple']:
                            print(f"警告：第{line_num}行题目类型无效: {question_type}")
                            continue
                        
                        try:
                            # 检查是否为范围格式（如 1-20 或 21-40）
                            if '-' in question_range:
                                range_parts = question_range.split('-')
                                if len(range_parts) == 2:
                                    start_num = int(range_parts[0].strip())
                                    end_num = int(range_parts[1].strip())
                                    
                                    # 为范围内的每个题号设置类型
                                    for num in range(start_num, end_num + 1):
                                        question_types[num] = question_type
                                    
                                    print(f"配置题目 {start_num}-{end_num} 为 {question_type}")
                                else:
                                    print(f"警告：第{line_num}行范围格式错误: {question_range}")
                            else:
                                # 单个题号
                                question_num = int(question_range)
                                question_types[question_num] = question_type
                                print(f"配置题目 {question_num} 为 {question_type}")
                                
                        except ValueError:
                            print(f"警告：第{line_num}行题号格式错误: {question_range}")
                    else:
                        print(f"警告：第{line_num}行格式错误: {line}")
                else:
                    print(f"警告：第{line_num}行缺少冒号分隔符: {line}")
    
    except Exception as e:
        print(f"读取题目类型配置文件失败: {e}")
    
    return question_types


def parse_multiple_choice_answers(file_path):
    """
    解析支持多选题的答案配置文件
    
    参数:
        file_path: 答案配置文件路径
    
    返回:
        tuple: (answers_dict, scores_dict, options_dict)
               answers_dict: {题号: 答案} (单选为字符串，多选为列表)
               scores_dict: {题号: 分值}
               options_dict: {题号: 选项个数}
    """
    answers = {}
    scores = {}
    options = {}
    
    if not os.path.exists(file_path):
        print(f"答案配置文件不存在: {file_path}")
        return answers, scores, options
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳过空行和注释行
                if not line or line.startswith('#'):
                    continue
                
                # 解析配置行：题号:答案:分值:选项个数
                parts = line.split(':')
                if len(parts) >= 3:
                    try:
                        question_num = int(parts[0].strip())
                        answer_str = parts[1].strip()
                        score_str = parts[2].strip()
                        
                        # 解析选项个数（如果提供）
                        option_count = 4  # 默认4个选项
                        if len(parts) >= 4:
                            option_count = int(parts[3].strip())
                        
                        # 解析答案（支持多选）
                        if ',' in answer_str:
                            # 多选题：分割并排序
                            answer_list = [ans.strip().upper() for ans in answer_str.split(',')]
                            answer_list.sort()  # 按字母顺序排序
                            answers[question_num] = answer_list
                        elif len(answer_str) > 1 and answer_str.isalpha():
                            # 多选题（无逗号分隔，如 "AC"）：拆分并排序
                            answer_list = list(answer_str.upper())
                            answer_list.sort()
                            answers[question_num] = answer_list
                        else:
                            # 单选题
                            answers[question_num] = answer_str.upper()
                        
                        # 解析分值
                        try:
                            scores[question_num] = float(score_str)
                        except ValueError:
                            print(f"警告：第{line_num}行分值格式错误: {score_str}")
                            scores[question_num] = 1.0  # 默认分值
                        
                        # 存储选项个数
                        options[question_num] = option_count
                        
                        print(f"题目 {question_num}: 答案={answers[question_num]}, 分值={scores[question_num]}, 选项数={option_count}")
                        
                    except ValueError as e:
                        print(f"警告：第{line_num}行格式错误: {line} - {e}")
                else:
                    print(f"警告：第{line_num}行格式不完整: {line}")
    
    except Exception as e:
        print(f"读取答案配置文件失败: {e}")
    
    return answers, scores, options


def compare_answers(student_answer, correct_answer):
    """
    比较学生答案和标准答案
    
    参数:
        student_answer: 学生答案（字符串或列表）
        correct_answer: 标准答案（字符串或列表）
    
    返回:
        bool: 是否正确
    """
    # 处理多选题
    if isinstance(correct_answer, list):
        if isinstance(student_answer, list):
            # 都是列表，比较排序后的结果
            return sorted(student_answer) == sorted(correct_answer)
        else:
            # 标准答案是多选，学生答案是单选，肯定错误
            return False
    
    # 处理单选题
    if isinstance(student_answer, list):
        # 标准答案是单选，学生答案是多选，肯定错误
        return False
    else:
        # 都是字符串，直接比较
        return str(student_answer).upper() == str(correct_answer).upper()


if __name__ == "__main__":
    # 测试代码
    print("=== 测试题目类型解析 ===")
    question_types = parse_question_types("question_types.txt")
    print(f"题目类型配置: {question_types}")
    
    print("\n=== 测试答案配置解析 ===")
    answers, scores, options = parse_multiple_choice_answers("answer_multiple.txt")
    print(f"答案配置: {answers}")
    print(f"分值配置: {scores}")
    print(f"选项配置: {options}")
    
    print("\n=== 测试答案比较 ===")
    test_cases = [
        (["A", "C"], ["A", "C"], True),  # 多选正确
        (["C", "A"], ["A", "C"], True),  # 多选正确（顺序不同）
        (["A"], ["A", "C"], False),      # 多选不完整
        ("A", "A", True),                # 单选正确
        ("A", "B", False),               # 单选错误
        (["A", "B"], "A", False),        # 类型不匹配
    ]
    
    for student, correct, expected in test_cases:
        result = compare_answers(student, correct)
        status = "✓" if result == expected else "✗"
        print(f"{status} 学生答案: {student}, 标准答案: {correct}, 结果: {result}")