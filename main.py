import sys
import csv
import re
import uuid
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QGridLayout, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QFont
from PyQt5.QtCore import Qt
import os


class GUIDReplacer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Замена GUID в XML по CSV (PyQt5)")
        self.resize(920, 600)
        self.guid_map = {}

        self.xml_file = ""
        self.csv_file = ""

        layout = QGridLayout()

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

        self.setLayout(layout)

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
        if not self.xml_input.text().strip() or not self.csv_input.text().strip():
            return
        if not os.path.isfile(self.xml_input.text().strip()) or not os.path.isfile(self.csv_input.text().strip()):
            return

        # Загрузить соответствия
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

        # Настройка форматов (цвета текста)
        fmt_old = QTextCharFormat()
        fmt_old.setForeground(QColor("red"))
        fmt_new = QTextCharFormat()
        fmt_new.setForeground(QColor("green"))

        cursor = self.text_preview.textCursor()
        cursor.beginEditBlock()

        # Одним проходом по тексту ищем и подсвечиваем все old_uid, вставляя новый (в скобках)
        pattern = re.compile(
            "|".join(map(re.escape, sorted(self.guid_map, key=len, reverse=True))))
        pos = 0
        offset = 0
        xml_text2 = xml_text  # Оригинал для поиска
        for match in pattern.finditer(xml_text2):
            old_uid = match.group()
            new_uid = self.guid_map[old_uid]
            start = match.start() + offset
            end = match.end() + offset

            # Выделить старый UID красным
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(fmt_old)
            cursor.clearSelection()
            # Вставить скобками новый UID сразу после старого, зелёным
            cursor.setPosition(end)
            cursor.insertText(f"({new_uid})", fmt_new)
            # Учесть смещение во всей строке (добавили символы!)
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

        # Чтение и замена (без скобок, только сами UID)
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
    sys.exit(app.exec_())
