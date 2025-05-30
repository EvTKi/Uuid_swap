import sys
import csv
import re
import uuid
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QGridLayout, QFileDialog, QMessageBox
)
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QFont
from PySide6.QtCore import Qt


class GUIDReplacer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Замена GUID в XML по CSV (PySide6)")
        self.resize(930, 650)
        self.guid_map = {}

        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)

        layout.addWidget(QLabel("XML-файл:"), 0, 0)
        self.xml_input = QLineEdit()
        layout.addWidget(self.xml_input, 0, 1)
        self.xml_btn = QPushButton("Выбрать...")
        self.xml_btn.clicked.connect(self.pick_xml)
        layout.addWidget(self.xml_btn, 0, 2)

        layout.addWidget(QLabel("CSV-файл:"), 1, 0)
        self.csv_input = QLineEdit()
        layout.addWidget(self.csv_input, 1, 1)
        self.csv_btn = QPushButton("Выбрать...")
        self.csv_btn.clicked.connect(self.pick_csv)
        layout.addWidget(self.csv_btn, 1, 2)

        self.replace_btn = QPushButton("Выполнить замену")
        self.replace_btn.clicked.connect(self.replace_guids)
        layout.addWidget(self.replace_btn, 2, 0, 1, 3)

        layout.addWidget(
            QLabel("Преобразованный XML с подсветкой:"), 3, 0, 1, 3)
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        font = QFont("Consolas", 10)
        self.text_preview.setFont(font)
        layout.addWidget(self.text_preview, 4, 0, 1, 3)

        # Файлы XML и CSV
        self.xml_file = ""
        self.csv_file = ""

    def pick_xml(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML-файл", "", "XML файлы (*.xml);;Все файлы (*)")
        if file_path:
            self.xml_file = file_path
            self.xml_input.setText(file_path)
            self.try_render_preview()

    def pick_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите CSV-файл", "", "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            self.csv_file = file_path
            self.csv_input.setText(file_path)
            self.try_render_preview()

    def try_render_preview(self):
        if not self.xml_input.text().strip() or not self.csv_input.text().strip():
            return
        if not os.path.isfile(self.xml_input.text().strip()) or not os.path.isfile(self.csv_input.text().strip()):
            return

        # Читаем таблицу соответствий
        try:
            with open(self.csv_input.text().strip(), newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                self.guid_map = {}
                for row in reader:
                    old_uid = row.get('old_uid', '').strip()
                    new_uid = row.get('new_uid', '').strip()
                    if old_uid:
                        if not new_uid:
                            new_uid = str(uuid.uuid4())
                        self.guid_map[old_uid] = new_uid
        except Exception as e:
            QMessageBox.critical(self, "Ошибка CSV", f"Ошибка чтения CSV: {e}")
            return

        try:
            with open(self.xml_input.text().strip(), encoding='utf-8') as xmlfile:
                xml_text = xmlfile.read()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка XML", f"Ошибка чтения XML: {e}")
            return

        self.text_preview.clear()
        self.text_preview.setPlainText(xml_text)

        # Настройка форматов (цвет + зачеркивание)
        fmt_old = QTextCharFormat()
        fmt_old.setForeground(QColor("red"))
        fmt_old.setFontStrikeOut(True)

        fmt_new = QTextCharFormat()
        fmt_new.setForeground(QColor("green"))

        cursor = self.text_preview.textCursor()
        cursor.beginEditBlock()

        # Регулярка для поиска всех old_uid
        pattern = re.compile(
            "|".join(map(re.escape, sorted(self.guid_map, key=len, reverse=True))))
        pos = 0
        offset = 0
        xml_text2 = xml_text
        for match in pattern.finditer(xml_text2):
            old_uid = match.group()
            new_uid = self.guid_map[old_uid]
            start = match.start() + offset
            end = match.end() + offset

            # Красный + зачеркнутый для старого UID
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt_old)
            cursor.clearSelection()

            # Вставить новый UID в скобках (зелёный)
            cursor.setPosition(end)
            cursor.insertText(f"({new_uid})", fmt_new)
            offset += len(f"({new_uid})")

        cursor.endEditBlock()
        self.text_preview.setTextCursor(cursor)

    def replace_guids(self):
        if not self.xml_input.text().strip() or not self.csv_input.text().strip():
            QMessageBox.warning(self, "Внимание", "Выберите оба файла!")
            return
        if not os.path.isfile(self.xml_input.text().strip()) or not os.path.isfile(self.csv_input.text().strip()):
            QMessageBox.warning(self, "Внимание", "Файлы не найдены!")
            return

        try:
            with open(self.xml_input.text().strip(), encoding='utf-8') as xmlfile:
                xml_text = xmlfile.read()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка XML", f"Ошибка чтения XML: {e}")
            return

        pattern = re.compile(
            "|".join(map(re.escape, sorted(self.guid_map, key=len, reverse=True))))

        def repl(m):
            return self.guid_map[m.group(0)]
        result_text = pattern.sub(repl, xml_text)

        base, ext = os.path.splitext(self.xml_input.text().strip())
        out_path = f"{base}_output{ext}"
        try:
            with open(out_path, "w", encoding="utf-8") as out:
                out.write(result_text)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка записи",
                                 f"Ошибка при записи файла: {e}")
            return

        QMessageBox.information(
            self, "Готово", f"Завершено! Новый файл: {out_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GUIDReplacer()
    win.show()
    sys.exit(app.exec())
