import sys
import os
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QGridLayout, QFileDialog,
    QMessageBox, QMenuBar, QVBoxLayout, QHBoxLayout
)
from PySide6.QtGui import (
    QTextCharFormat, QColor, QTextCursor, QFont, QShortcut, QKeySequence, QPalette, QAction
)
from PySide6.QtCore import Qt

import backend  # backend.py должен быть рядом


class GUIDReplacer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Замена GUID в XML по CSV (PySide6 с поиском и темами)")
        self.resize(940, 800)
        self.current_theme = "light"

        # --- Меню ---
        layout = QVBoxLayout(self)
        self.menubar = QMenuBar(self)
        menu_theme = self.menubar.addMenu("Тема")
        self.action_light = QAction("Светлая", self)
        self.action_dark = QAction("Тёмная", self)
        self.action_light.setCheckable(True)
        self.action_dark.setCheckable(True)
        self.action_light.setChecked(True)
        menu_theme.addAction(self.action_light)
        menu_theme.addAction(self.action_dark)
        self.action_light.triggered.connect(lambda: self.set_theme('light'))
        self.action_dark.triggered.connect(lambda: self.set_theme('dark'))
        layout.setMenuBar(self.menubar)

        # --- Поля и кнопки выбора файлов ---
        grid = QGridLayout()
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

        # --- Search bar ---
        grid.addWidget(QLabel("Преобразованный XML с подсветкой:"), 3, 0, 1, 3)
        search_layout = QHBoxLayout()
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Поиск...")
        self.search_prev_btn = QPushButton("Назад ↑")
        self.search_next_btn = QPushButton("Вперёд ↓")
        search_layout.addWidget(self.search_line)
        search_layout.addWidget(self.search_prev_btn)
        search_layout.addWidget(self.search_next_btn)
        grid.addLayout(search_layout, 4, 0, 1, 3)

        self.search_prev_btn.clicked.connect(
            lambda: self.find_next(backward=True))
        self.search_next_btn.clicked.connect(self.find_next)
        self.search_line.returnPressed.connect(self.find_next)

        # --- QTextEdit для предпросмотра ---
        self.text_preview = QTextEdit()
        self.text_preview.setFont(QFont("Consolas", 10))
        self.text_preview.setReadOnly(True)
        grid.addWidget(self.text_preview, 5, 0, 1, 3)

        layout.addLayout(grid)

        # Горячие клавиши
        QShortcut(QKeySequence("Ctrl+O"), self, self.pick_xml)
        QShortcut(QKeySequence("Ctrl+S"), self, self.replace_guids)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)

        # Поисковые переменные
        self._search_indices = []
        self._search_current = -1
        self._search_pattern_last = ""

        # Вспомогательные переменные
        self.guid_map = {}
        self.xml_file = ""
        self.csv_file = ""

        self.set_theme("light")

    def set_theme(self, theme):
        app = QApplication.instance()
        if theme == "light":
            app.setStyle("Fusion")
            palette = QPalette()
            palette.setColor(QPalette.Window, Qt.white)
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, Qt.white)
            palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
            palette.setColor(QPalette.ToolTipBase, Qt.black)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(232, 232, 232))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Highlight, QColor(38, 79, 120))
            palette.setColor(QPalette.HighlightedText, Qt.white)
            app.setPalette(palette)
            self.action_light.setChecked(True)
            self.action_dark.setChecked(False)
        else:
            app.setStyle("Fusion")
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(30, 30, 30))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(32, 32, 32))
            palette.setColor(QPalette.AlternateBase, QColor(44, 44, 44))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(44, 44, 44))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Highlight, QColor(38, 79, 120))
            palette.setColor(QPalette.HighlightedText, Qt.white)
            app.setPalette(palette)
            self.action_light.setChecked(False)
            self.action_dark.setChecked(True)
        self.current_theme = theme

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
            self.text_preview.clear()
            return
        try:
            self.guid_map = backend.load_guid_map(csv_path)
            xml_text = backend.read_text_file(xml_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка чтения", str(e))
            return

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
            cursor.insertText(xml_text[pos:start], fmt_plain)
            cursor.insertText(xml_text[start:end], fmt_old)
            cursor.insertText(f"({new_uid})", fmt_new)
            pos = end
        cursor.insertText(xml_text[pos:], fmt_plain)

        # Сброс поиска
        self._search_indices = []
        self._search_current = -1
        self._search_pattern_last = ""
        self.text_preview.setExtraSelections([])

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

    # ---------- ПОИСК ----------
    def focus_search(self):
        self.search_line.setFocus()

    def find_next(self, backward=False):
        pattern = self.search_line.text()
        if not pattern:
            self.text_preview.setExtraSelections([])
            self._search_indices = []
            self._search_current = -1
            self._search_pattern_last = ""
            return

        text = self.text_preview.toPlainText()
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

        # При новом шаблоне сбрасываем индексы
        if pattern != self._search_pattern_last:
            self._search_indices = [(m.start(), m.end())
                                    for m in regex.finditer(text)]
            self._search_current = -1
            self._search_pattern_last = pattern

        num_matches = len(self._search_indices)
        if not num_matches:
            self.text_preview.setExtraSelections([])
            return

        # Циклический переход
        if backward:
            if self._search_current == -1:
                self._search_current = num_matches - 1
            else:
                self._search_current = (self._search_current - 1) % num_matches
        else:
            self._search_current = (self._search_current + 1) % num_matches

        sel_start, sel_end = self._search_indices[self._search_current]

        # setExtraSelections для текущего совпадения (НЕ меняет существующий стиль текста)
        selection = QTextEdit.ExtraSelection()
        search_fmt = QTextCharFormat()
        search_fmt.setBackground(QColor('#fff69b'))  # светло-жёлтый для поиска
        selection.format = search_fmt
        selection.cursor = self.text_preview.textCursor()
        selection.cursor.setPosition(sel_start)
        selection.cursor.setPosition(sel_end, QTextCursor.KeepAnchor)
        self.text_preview.setExtraSelections([selection])

        # Прокрутка и видимый курсор
        cursor = self.text_preview.textCursor()
        cursor.setPosition(sel_start)
        cursor.setPosition(sel_end, QTextCursor.KeepAnchor)
        self.text_preview.setTextCursor(cursor)
        self.text_preview.ensureCursorVisible()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GUIDReplacer()
    win.show()
    sys.exit(app.exec())
