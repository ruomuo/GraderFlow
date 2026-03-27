import os
import sys
import cv2

RUN_DATE = "2026-03-26"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.omr.question_parser import parse_question_types, parse_multiple_choice_answers
from core.omr.recognizer import recognize_answer_sheet


def main():
    cv2.imshow = lambda *args, **kwargs: None
    cv2.waitKey = lambda *args, **kwargs: 0
    cv2.destroyAllWindows = lambda *args, **kwargs: None

    image_path = os.path.join(PROJECT_ROOT, "runs", "detect", "exp", "crops", "answerArea", "sheet04.jpg")
    question_types_path = os.path.join(PROJECT_ROOT, "config", "answer_config", "question_types.txt")
    answer_config_path = os.path.join(PROJECT_ROOT, "config", "answer_config", "answer_multiple.txt")

    print(f"RUN_DATE={RUN_DATE}")
    print(f"IMAGE={image_path}")

    question_types = parse_question_types(question_types_path)
    _, _, options_config = parse_multiple_choice_answers(answer_config_path)
    result, question_options = recognize_answer_sheet(
        image_path,
        question_types=question_types,
        options_config=options_config,
        start_question_num=1,
    )

    print("识别结果:")
    for question_num in sorted(result.keys()):
        print(f"  题目 {question_num}: {result[question_num]}")

    print("详细面积排序:")
    for question_num in sorted(question_options.keys()):
        if not isinstance(question_num, int):
            continue
        options_list = question_options[question_num]
        sorted_options = sorted(options_list, key=lambda x: x["area"], reverse=True)
        area_text = ", ".join([f'{opt["option"]}:{opt["area"]}:{int(opt["filled"])}' for opt in sorted_options])
        print(f"  Q{question_num}: {area_text}")


if __name__ == "__main__":
    main()
