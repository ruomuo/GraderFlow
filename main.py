import sys
import os
from PySide6.QtWidgets import QApplication, QDialog
from interface.main_window import OMRGUI
from utils.activation import ActivationManager
from interface.dialogs.activation_dialog import ActivationDialog

def main():
    app = QApplication(sys.argv)
    
    # Ensure the root directory is in sys.path
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # 激活/试用检查
    activation_manager = ActivationManager()
    
    # 如果未激活，显示激活/试用对话框
    if not activation_manager.is_activated():
        dialog = ActivationDialog()
        if dialog.exec() != QDialog.Accepted:
            sys.exit(0)
        
    window = OMRGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
