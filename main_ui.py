# main_ui.py
import sys
import os
import re
import io
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, QGridLayout, QFileDialog,
    QMessageBox, QMenuBar, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QSplitter
)
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QFont, QShortcut, QKeySequence, QPalette, QAction
from PySide6.QtCore import Qt

import backend  # backend.py должен быть рядом


class GUIDReplacer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Замена GUID в XML по CSV (PySide6 — CIM XML, поиск, темы, структура)")
        self.resize(1200, 860)
        self.current_theme = "light"

        layout = QVBoxLayout(self)

        # --- Меню ---
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

        # --- Splitter: слева дерево XML, справа UI и предпросмотр ---
        self.splitter = QSplitter(self)
        layout.addWidget(self.splitter)

        # -- Левая панель: дерево структуры XML --
        self.tree_xml = QTreeWidget()
        self.tree_xml.setHeaderLabel("Структура XML")
        self.splitter.addWidget(self.tree_xml)
        self.tree_xml.setMinimumWidth(280)
        self.tree_xml.itemClicked.connect(self.xmltree_item_clicked)
        self.tag_parent_map = []
        # -- Правая панель: всё остальное
        container = QWidget()
        grid = QGridLayout(container)
        self.splitter.addWidget(container)
        self.splitter.setSizes([320, 880])

        split_label = QLabel("Преобразованный XML с подсветкой:")
        grid.addWidget(split_label, 0, 0, 1, 3)

        # --- Поля и кнопки выбора файлов ---
        grid.addWidget(QLabel("XML-файл:"), 1, 0)
        self.xml_input = QLineEdit()
        grid.addWidget(self.xml_input, 1, 1)
        self.xml_btn = QPushButton("Выбрать...")
        grid.addWidget(self.xml_btn, 1, 2)
        self.xml_btn.clicked.connect(self.pick_xml)
        grid.addWidget(QLabel("CSV-файл:"), 2, 0)
        self.csv_input = QLineEdit()
        grid.addWidget(self.csv_input, 2, 1)
        self.csv_btn = QPushButton("Выбрать...")
        grid.addWidget(self.csv_btn, 2, 2)
        self.csv_btn.clicked.connect(self.pick_csv)
        self.replace_btn = QPushButton("Выполнить замену")
        grid.addWidget(self.replace_btn, 3, 0, 1, 3)
        self.replace_btn.clicked.connect(self.replace_guids)

        # --- Search bar (поиск, циклический) ---
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

        # Горячие клавиши
        QShortcut(QKeySequence("Ctrl+O"), self, self.pick_xml)
        QShortcut(QKeySequence("Ctrl+S"), self, self.replace_guids)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)

        # Поисковые переменные
        self._search_indices = []
        self._search_current = -1
        self._search_pattern_last = ""

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
            base_gray = QColor(122, 122, 122)        # #7A7A7A
            dark_gray = QColor(80, 80, 80)           # #505050
            palette.setColor(QPalette.Window, base_gray)
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, dark_gray)
            palette.setColor(QPalette.AlternateBase, base_gray)
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, base_gray)
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Highlight, QColor(61, 174, 233))
            palette.setColor(QPalette.HighlightedText, Qt.black)
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
        self.text_preview.clear()
        self.tree_xml.clear()
        if not (os.path.isfile(xml_path) and os.path.isfile(csv_path)):
            return
        try:
            self.guid_map = backend.load_guid_map(csv_path)
            xml_text = backend.read_text_file(xml_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка чтения", str(e))
            return

        # Только если мы без исключений прочитали xml_text, работаем дальше!
        # Формирование предпросмотра с выделением uid и новых значений
        highlights = backend.find_uid_matches(xml_text, self.guid_map)
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

        # --- АНАЛИЗ СТРУКТУРЫ XML ---
        self.build_xml_tree_with_ns(xml_text)
        self.tag_parent_map = self.build_tag_parent_map(xml_text)

        # Сброс поиска
        self._search_indices = []
        self._search_current = -1
        self._search_pattern_last = ""
        self.text_preview.setExtraSelections([])

    def build_tag_parent_map(self, xml_text):
        """
        Составляет карту: (parent_tag, parent_uid, child_tag, child_attribs, start_pos)
        """
        import xml.etree.ElementTree as ET
        import re

        tag_parent_map = []
        PAT = re.compile(r"<([a-zA-Z0-9_:\-\.]+)\b([^>]*)>")

        # Avoid parsing errors
        safe_xml = xml_text
        if not re.match(r"\s*<\?xml", safe_xml):
            safe_xml = "<ROOT>\n" + safe_xml + "\n</ROOT>"

        try:
            et = ET.ElementTree(ET.fromstring(safe_xml))
        except Exception:
            return []

        # Собираем все стартовые позиции интересующего тега в тексте
        matches = list(PAT.finditer(xml_text))
        ci = 0  # current index in matches

        for parent in et.iter():
            parent_tag = parent.tag
            parent_about = parent.attrib.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about') or \
                parent.attrib.get('rdf:about')
            for child in parent:
                child_tag = child.tag
                child_attribs = child.attrib.copy()
                child_resource = child.attrib.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource') or \
                    child.attrib.get('rdf:resource')

                # Нам интересны дочерние теги, можно сузить до конкретного типа
                # например, Folder.CreatingNode:
                if child_tag.endswith('Folder.CreatingNode'):
                    # ищем start_pos для этого child_tag в исходном тексте
                    # Используем resource для точности
                    start_pos = None
                    while ci < len(matches):
                        m = matches[ci]
                        name = m.group(1)
                        attrs = m.group(2)
                        ci += 1
                        if name.endswith('Folder.CreatingNode'):
                            if child_resource and child_resource in attrs:
                                start_pos = m.start()
                                break
                            elif not child_resource:
                                start_pos = m.start()
                                break
                    tag_parent_map.append((
                        parent_tag, parent_about, child_tag, child_resource, start_pos
                    ))
        return tag_parent_map

    def build_xml_tree_with_ns(self, xml_text):
        import io
        import xml.etree.ElementTree as ET
        from xml.etree.ElementTree import ParseError
        import re

        self.tree_xml.clear()

        # — есть ли корректный корень? (например, <rdf:RDF ...> после <?xml ?>)
        txt = xml_text.lstrip()
        root_tag_match = re.match(
            r"(<\?xml\b[^>]*\?>)?\s*<([a-zA-Z0-9_:\-]+)", txt)
        if root_tag_match:
            root_tag = root_tag_match.group(2)
            has_root = True
        else:
            has_root = False

        try:
            safe_xml = xml_text.lstrip()
            if not has_root or root_tag.upper() == 'XML':
                # Удаляем xml-declaration, если есть
                safe_xml = re.sub(
                    r"<\?xml\b[^>]*\?>", "", safe_xml, count=1).lstrip()
                safe_xml = "<ROOT>\n" + safe_xml + "\n</ROOT>"

            # Разбираем namespace prefix <-> uri
            ns_map = dict(re.findall(
                r'xmlns:([A-Za-z0-9_]+)="([^"]+)"', safe_xml))
            ns_uri2prefix = {uri: prefix for prefix, uri in ns_map.items()}

            context = ET.iterparse(io.StringIO(
                safe_xml), events=("start", "end"))
            parents = []
            elem2item = {None: None}
            for event, elem in context:
                if event == "start":
                    tag = elem.tag
                    if "}" in tag:
                        nsuri, shorttag = tag[1:].split("}")
                        prefix = ns_uri2prefix.get(nsuri, "")
                        tag = f"{prefix}:{shorttag}" if prefix else shorttag
                    label = tag
                    uid = (elem.attrib.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
                           or elem.attrib.get('rdf:about')
                           or elem.attrib.get('rdf:resource')
                           or elem.attrib.get('about')
                           or elem.attrib.get('resource'))
                    if uid:
                        label += f" [{uid}]"
                    node = QTreeWidgetItem([label])
                    node.setData(0, Qt.UserRole, (tag, elem.attrib.copy()))
                    if parents:
                        parent_item = elem2item[parents[-1]]
                        if parent_item:
                            parent_item.addChild(node)
                    else:
                        self.tree_xml.addTopLevelItem(node)
                    elem2item[elem] = node
                    parents.append(elem)
                elif event == "end":
                    parents.pop()
            self.tree_xml.expandToDepth(2)
        except ParseError as e:
            self.tree_xml.addTopLevelItem(QTreeWidgetItem(
                [f"XML с ошибкой структуры ({str(e)})"]))

    def get_namespace_map(self, xml_text):
        # Префиксы xmlns:... и основное пространство имён
        ns_map = dict(re.findall(r'xmlns:([A-Za-z0-9_]+)="([^"]+)"', xml_text))
        return ns_map

    def xmltree_item_clicked(self, item, column):
        tag, attrib = item.data(0, Qt.UserRole) or (None, {})
        if not tag:
            return
        parent_item = item.parent()
        parent_tag = parent_about = None
        if parent_item:
            parent_tag, parent_attrib = parent_item.data(
                0, Qt.UserRole) or (None, {})
            parent_about = (
                parent_attrib.get(
                    '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
                or parent_attrib.get('rdf:about')
                or parent_attrib.get('about')
            )

        # === added/changed ===
        # Если клик по Folder.CreatingNode — ищем только ту пару, где родитель совпадает!
        if tag.endswith("Folder.CreatingNode") and self.tag_parent_map:
            # Берём resource текущего
            resource = attrib.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource') or attrib.get(
                'rdf:resource') or attrib.get('resource')

            for (ptag, pabout, ctag, cres, start_pos) in self.tag_parent_map:
                if (
                    ptag == parent_tag and
                    pabout == parent_about and
                    ctag.endswith("Folder.CreatingNode") and
                    resource == cres and
                    start_pos is not None
                ):
                    cursor = self.text_preview.textCursor()
                    cursor.setPosition(start_pos)
                    self.text_preview.setTextCursor(cursor)
                    self.text_preview.ensureCursorVisible()
                    return  # Нашли и перешли, выход
        # === /added ===

        # Если не Folder.CreatingNode или не нашли — как раньше, по названию
        text = self.text_preview.toPlainText()
        pattern = f"<{tag}"
        idx = text.find(pattern)
        if idx == -1:
            matches = re.findall(rf"<([a-zA-Z0-9_]+):{tag}", text)
            if matches:
                pattern = f"<{matches[0]}:{tag}"
                idx = text.find(pattern)
        if idx == -1:
            return
        endidx = text.find(">", idx)
        if endidx < idx:
            endidx = idx + len(tag)
        cursor = self.text_preview.textCursor()
        cursor.setPosition(idx)
        cursor.setPosition(endidx + 1, QTextCursor.KeepAnchor)
        self.text_preview.setTextCursor(cursor)
        self.text_preview.ensureCursorVisible()

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

        if pattern != self._search_pattern_last:
            self._search_indices = [(m.start(), m.end())
                                    for m in regex.finditer(text)]
            self._search_current = -1
            self._search_pattern_last = pattern

        num_matches = len(self._search_indices)
        if not num_matches:
            self.text_preview.setExtraSelections([])
            return

        if backward:
            if self._search_current == -1:
                self._search_current = num_matches - 1
            else:
                self._search_current = (self._search_current - 1) % num_matches
        else:
            self._search_current = (self._search_current + 1) % num_matches

        sel_start, sel_end = self._search_indices[self._search_current]
        selection = QTextEdit.ExtraSelection()
        search_fmt = QTextCharFormat()
        search_fmt.setBackground(QColor('#fff69b'))
        selection.format = search_fmt
        selection.cursor = self.text_preview.textCursor()
        selection.cursor.setPosition(sel_start)
        selection.cursor.setPosition(sel_end, QTextCursor.KeepAnchor)
        self.text_preview.setExtraSelections([selection])

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
