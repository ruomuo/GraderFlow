import hashlib
import sys

# 必须与 core/license_manager.py 中的 SECRET_KEY 保持一致
SECRET_KEY = "OMR_SYSTEM_2025_SECRET_KEY_SALT_!@#"

def generate_code(machine_id):
    """
    根据机器码生成激活码
    """
    machine_id = machine_id.strip().upper()
    if len(machine_id) != 16:
        print("警告: 机器码长度通常为16位，请确认是否正确。")
    
    raw = f"{machine_id}{SECRET_KEY}ACTIVATED"
    # 取 MD5 的中间 16 位作为激活码
    code = hashlib.md5(raw.encode()).hexdigest().upper()[8:24]
    return code

if __name__ == "__main__":
    print("=== 智能阅卷系统 激活码生成器 ===")
    if len(sys.argv) > 1:
        mid = sys.argv[1]
    else:
        mid = input("请输入客户提供的机器码: ").strip()
    
    if mid:
        code = generate_code(mid)
        print(f"\n机器码: {mid}")
        print(f"激活码: {code}")
        print("\n请将激活码发送给客户。")
    else:
        print("未输入机器码。")
