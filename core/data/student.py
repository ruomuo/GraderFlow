class StudentInfo:
    def __init__(self):
        self.name = ""  # 姓名识别结果
        self.student_id = ""  # 学号识别结果
        self.answers = {}  # 改为字典存储，键为题号(int)，值为答案(str)
        self.correct_answers = {}  # 新增：正确答案对照
        self.wrong_questions = []  # 错题列表（int类型题号）
        self.blank_questions = []  # 新增：未填涂题目列表
        self.score = 0  # 总分
        self.objective_score = 0 # 客观题得分
        self.subjective_score = 0 # 主观题得分
        self.subjective_results = {}  # 主观题详细评分结果
        self.error = None  # 错误信息
        self.recognition_log = []  # 新增：识别过程日志
        self.question_scores = {} #题号(int) → 得分(float)
        self.has_name_id = False  # 新增：标记是否成功识别姓名和学号
        self.image_path = ""  # 新增：试卷图片路径
        self.detailed_answers = {}  # 新增：详细选项信息（包含坐标）

    def calculate_score(self, answer_key: dict, question_types: dict = None, scoring_rule: str = "standard"):
        """
        根据答案配置计算得分（支持单选题和多选题）
        修复：即使姓名学号未识别，也能正常计算客观题得分

        参数：
            answer_key: 解析后的答案字典，格式为 {题号: {'answer': 'A', 'score': 2}} 或 {题号: {'answer': ['A', 'B'], 'score': {'A': 1, 'B': 1}}}
            question_types: 题目类型字典，格式为 {题号: 'single'/'multiple'}

        返回：
            总得分、错误题号列表、空白题号列表
        """
        self.correct_answers = answer_key
        total_score = 0

        # 检查姓名和学号是否识别成功（修改为只要有一个识别成功就算部分成功）
        self.has_name_id = bool(self.name or self.student_id)
        
        # 即使姓名学号未识别，也继续计算客观题得分
        for q_num, correct_info in answer_key.items():
            user_ans = self.answers.get(q_num, "未填涂")
            
            if user_ans != "未填涂":
                # 只对字符串类型的答案转大写，列表类型保持不变
                if isinstance(user_ans, str):
                    user_ans = user_ans.upper().strip()  # 统一转为大写并去除空格
                elif isinstance(user_ans, list):
                    # 对列表中的每个元素转大写并去除空格
                    user_ans = [ans.upper().strip() if isinstance(ans, str) else ans for ans in user_ans]
            
            correct_ans = correct_info['answer']
            question_score = correct_info['score']
            
            # 获取题目类型，默认为单选题
            q_type = question_types.get(q_num, 'single') if question_types else 'single'

            # 分情况统计
            if user_ans == "未填涂":
                self.blank_questions.append(q_num)
                self.question_scores[q_num] = 0.0
            elif scoring_rule == "partial_penalty":
                if isinstance(correct_ans, list):
                    correct_choices = set(correct_ans)
                elif isinstance(correct_ans, str):
                    correct_choices = set(list(correct_ans)) if len(correct_ans) > 1 else {correct_ans}
                else:
                    correct_choices = set()

                if isinstance(user_ans, list):
                    user_choices = set(user_ans)
                elif isinstance(user_ans, str):
                    user_choices = set(list(user_ans)) if user_ans else set()
                else:
                    user_choices = set()

                if correct_choices:
                    right_count = len(user_choices & correct_choices)
                    wrong_count = len(user_choices - correct_choices)
                    raw_ratio = (right_count - wrong_count) / float(len(correct_choices))
                    if raw_ratio > 0:
                        question_score_value = question_score * raw_ratio
                        total_score += question_score_value
                        self.question_scores[q_num] = question_score_value
                    else:
                        self.wrong_questions.append(q_num)
                        self.question_scores[q_num] = 0.0
                else:
                    if user_ans == correct_ans:
                        total_score += question_score
                        self.question_scores[q_num] = question_score
                    else:
                        self.wrong_questions.append(q_num)
                        self.question_scores[q_num] = 0.0
            elif q_type == 'single':
                # 单选题：完全匹配才得分
                if user_ans == correct_ans:
                    total_score += question_score
                    self.question_scores[q_num] = question_score
                else:
                    self.wrong_questions.append(q_num)
                    self.question_scores[q_num] = 0.0
            elif q_type == 'multiple':
                # 多选题：全对才得分，漏选或错选都不得分
                if isinstance(correct_ans, list):
                    # 新格式：多选题答案为列表
                    user_choices = set(list(user_ans)) if user_ans else set()
                    correct_choices = set(correct_ans)
                    
                    # 完全匹配才得分
                    if user_choices == correct_choices:
                        total_score += question_score
                        self.question_scores[q_num] = question_score
                    else:
                        self.wrong_questions.append(q_num)
                        self.question_scores[q_num] = 0.0
                else:
                    # 兼容旧格式：将字符串答案按字符拆分处理
                    if isinstance(correct_ans, str):
                        correct_choices = set(list(correct_ans))
                        user_choices = set(list(user_ans)) if user_ans else set()
                        
                        # 多选题评分：完全匹配才得满分
                        if user_choices == correct_choices:
                            total_score += question_score
                            self.question_scores[q_num] = question_score
                        else:
                            self.wrong_questions.append(q_num)
                            self.question_scores[q_num] = 0.0
                    else:
                        # 其他情况按单选题处理
                        if user_ans == correct_ans:
                            total_score += question_score
                            self.question_scores[q_num] = question_score
                        else:
                            self.wrong_questions.append(q_num)
                            self.question_scores[q_num] = 0.0

        if scoring_rule == "partial_penalty":
            total_questions = len(answer_key)
            if total_questions > 0:
                normalized = (total_score / float(total_questions)) * 100
            else:
                normalized = 0
            self.objective_score = round(normalized, 2)
        else:
            self.objective_score = round(total_score, 2)

        self.score = round(self.objective_score + self.subjective_score, 2)
        return self.score

    def add_subjective_scores(self, subjective_results: dict):
        """
        添加主观题评分结果
        
        参数:
            subjective_results: 主观题评分结果字典
            格式: {question_num: {'score': int, 'max_score': int, 'details': str}}
        """
        self.subjective_results = subjective_results
        
        # 计算主观题总分
        subjective_total = 0
        for question_num, result in subjective_results.items():
            score = result.get("score", 0)
            subjective_total += score
            self.question_scores[question_num] = score
        
        self.subjective_score = subjective_total
        self.score = self.objective_score + self.subjective_score

    def add_recognition_log(self, log_entry: str):
        """添加识别过程日志"""
        self.recognition_log.append(f"{len(self.recognition_log) + 1}. {log_entry}")

    def result_summary(self) -> str:
        """生成结果摘要"""
        try:
            from utils.config_manager import config_manager
            scoring_rule = config_manager.get_objective_scoring_rule()
        except Exception:
            scoring_rule = "standard"

        objective_possible_score = sum(info['score'] for info in self.correct_answers.values())
        if scoring_rule == "partial_penalty":
            objective_possible_score = 100.0
        total_possible_score = objective_possible_score + sum(result.get('max_score', 0) for result in self.subjective_results.values())
        
        # 姓名学号显示处理
        name_display = self.name if self.name else "未识别"
        id_display = self.student_id if self.student_id else "未识别"
        
        summary = f"学生信息：{name_display} ({id_display})\n"
        
        # 如果姓名学号未完全识别，添加警告
        if not (self.name and self.student_id):
            if self.name or self.student_id:
                summary += "⚠️ 警告：姓名或学号部分识别，请人工核实\n"
            else:
                summary += "⚠️ 警告：姓名和学号均未识别，请人工核实\n"
        
        summary += f"总得分：{self.score:.1f}/{total_possible_score:.1f}\n"
        
        if self.objective_score > 0:
            summary += f"客观题得分：{self.objective_score:.1f}\n"
        
        if self.subjective_score > 0:
            summary += f"主观题得分：{self.subjective_score:.1f}\n"
            
        summary += f"错题数：{len(self.wrong_questions)}\n"
        summary += f"未作答：{len(self.blank_questions)}"
        
        return summary

    def get_detailed_report(self) -> str:
        """生成详细报告"""
        report = self.result_summary() + "\n\n"
        
        if self.wrong_questions:
            report += f"错题详情：{', '.join(map(str, self.wrong_questions))}\n"
        
        if self.blank_questions:
            report += f"未作答题目：{', '.join(map(str, self.blank_questions))}\n"
        
        if self.subjective_results:
            report += "\n主观题评分详情：\n"
            for q_num, result in self.subjective_results.items():
                report += f"第{q_num}题：{result.get('score', 0)}/{result.get('max_score', 0)}分\n"
                report += f"评分详情：{result.get('details', '无详情')}\n"
        
        return report
