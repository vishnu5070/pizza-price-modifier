STYLE_SHEET = """
QWidget {
    background-color: #ffffff;
    color: #000000;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 14px;
}

QLabel {
    color: #000000;
}

QLabel#HeaderLabel {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 20px;
}

QLabel#SubHeaderLabel {
    font-size: 18px;
    font-weight: bold;
    margin-top: 10px;
    margin-bottom: 10px;
}

QLineEdit {
    padding: 8px;
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: #f9f9f9;
}

QLineEdit:focus {
    border: 1px solid #000000;
    background-color: #ffffff;
}

QPushButton {
    padding: 10px 20px;
    background-color: #000000;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #333333;
}

QPushButton:pressed {
    background-color: #555555;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}

QComboBox {
    padding: 8px;
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: #ffffff;
}

QComboBox::drop-down {
    border-left: 1px solid #cccccc;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    gridline-color: #eeeeee;
}

QHeaderView::section {
    background-color: #f0f0f0;
    padding: 6px;
    border: 1px solid #cccccc;
    font-weight: bold;
}
"""
#here im addding a new line in vishnu 