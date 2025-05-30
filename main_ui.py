# main_ui.py

import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QGridLayout, QFileDialog, QMessageBox
)
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QFont, QShortcut, QKeySequence
from PySide6.QtCore import Qt
import backend  # ваш backend.py должен быть рядом или в PYTHONPATH


class GUIDReplacer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Замена GUID в XML по CSV (PySide6, разделено на UI и backend)")
        self.resize(940, 700)

        grid = QGridLayout(self)
        self.xml_input = QLineEdit()
        self.csv_input = QLineEdit()
        grid.addWidget(QLabel("XML-файл:"), 0, 0)
        grid.addWidget(self.xml_input, 0, 1)
        self.xml_btn = QPushButton("Выбрать...")
        grid.addWidget(self.xml_btn, 0, 2)
        self.xml_btn.clicked.connect(self.pick_xml)

        grid.addWidget(QLabel("CSV-файл:"), 1, 0)
        grid.addWidget(self.csv_input, 1, 1)
        self.csv_btn = QPushButton("Выбрать...")
        grid.addWidget(self.csv_btn, 1, 2)
        self.csv_btn.clicked.connect(self.pick_csv)

        self.replace_btn = QPushButton("Выполнить замену")
        grid.addWidget(self.replace_btn, 2, 0, 1, 3)
        self.replace_btn.clicked.connect(self.replace_guids)

        grid.addWidget(QLabel("Преобразованный XML с подсветкой:"), 3, 0, 1, 3)
        self.text_preview = QTextEdit()
        self.text_preview.setFont(QFont("Consolas", 10))
        self.text_preview.setReadOnly(True)
        grid.addWidget(self.text_preview, 4, 0, 1, 3)

        # Горячие клавиши: (позже дополним)
        QShortcut(QKeySequence("Ctrl+O"), self, self.pick_xml)
        QShortcut(QKeySequence("Ctrl+S"), self, self.replace_guids)
        # поиск будет позже
        # QShortcut(QKeySequence("Ctrl+F"), self, ...)

        # Вспомогательные переменные
        self.guid_map = {}
        self.xml_file = ""
        self.csv_file = ""

    def pick_xml(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML-файл", "", "XML files (*.xml);;All files (*)")
        if file_path:
            self.xml_file = file_path
            self.xml_input.setText(file_path)
            self.try_render_preview()

    def pick_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите CSV-файл", "", "CSV files (*.csv);;All files (*)")
        if file_path:
            self.csv_file = file_path
            self.csv_input.setText(file_path)
            self.try_render_preview()

    def try_render_preview(self):
        xml_path = self.xml_input.text().strip()
        csv_path = self.csv_input.text().strip()
        if not (os.path.isfile(xml_path) and os.path.isfile(csv_path)):
            return

        try:
            self.guid_map = backend.load_guid_map(csv_path)
            xml_text = backend.read_text_file(xml_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка чтения", str(e))
            return

        # Выделение всех old_uid и добавление новых
        highlights = backend.find_uid_matches(xml_text, self.guid_map)
        self.text_preview.clear()
        fmt_plain = QTextCharFormat()
        fmt_old = QTextCharFormat()
        fmt_old.setForeground(QColor("red"))
        fmt_old.setFontStrikeOut(True)
        fmt_new = QTextCharFormat()
        fmt_new.setForeground(QColor("green"))
        cursor = self.text_preview.textCursor()
        pos = 0
        for start, end, old_uid, new_uid in highlights:
            # до uid
            cursor.insertText(xml_text[pos:start], fmt_plain)
            # старый uid (FULL)
            cursor.insertText(xml_text[start:end], fmt_old)
            # новый uid (скобки)
            cursor.insertText(f"({new_uid})", fmt_new)
            pos = end
        cursor.insertText(xml_text[pos:], fmt_plain)

    def replace_guids(self):
        xml_path = self.xml_input.text().strip()
        csv_path = self.csv_input.text().strip()
        if not (os.path.isfile(xml_path) and os.path.isfile(csv_path)):
            QMessageBox.warning(self, "Внимание", "Выберите оба файла!")
            return
        try:
            guid_map = backend.load_guid_map(csv_path)
            xml_text = backend.read_text_file(xml_path)
            result_text = backend.replace_guids(xml_text, guid_map)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка замены", str(e))
            return
        base, ext = os.path.splitext(xml_path)
        out_path = f"{base}_output{ext}"
        try:
            backend.save_text_file(out_path, result_text)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка записи", str(e))
            return
        QMessageBox.information(
            self, "Готово", f"Завершено! Новый файл: {out_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GUIDReplacer()
    win.show()
    sys.exit(app.exec())
