# backend.py

import csv
import re
import uuid
import os


def load_guid_map(csv_path):
    """
    Загружает соответствия из CSV и возвращает dict {old_uid: new_uid}
    """
    guid_map = {}
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                old_uid = row.get('old_uid', '').strip()
                new_uid = row.get('new_uid', '').strip()
                if old_uid:
                    if not new_uid:
                        new_uid = str(uuid.uuid4())
                    guid_map[old_uid] = new_uid
    except Exception as e:
        raise RuntimeError(f'Ошибка чтения CSV: {e}')
    return guid_map


def read_text_file(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f'Ошибка чтения файла {path}: {e}')


def save_text_file(path, text):
    try:
        with open(path, "w", encoding='utf-8') as f:
            f.write(text)
    except Exception as e:
        raise RuntimeError(f'Ошибка записи файла {path}: {e}')


def find_uid_matches(xml_text, guid_map):
    """
    Находит ВСЕ вхождения old_uid в строке xml_text (возвращает список из tuple: (start, end, old_uid, new_uid))
    Дубликаты uid поддерживаются.
    """
    if not guid_map:
        return []
    matches = []
    pattern = re.compile(
        "|".join(map(re.escape, sorted(guid_map, key=len, reverse=True))))
    for m in pattern.finditer(xml_text):
        old_uid = m.group()
        new_uid = guid_map[old_uid]
        matches.append((m.start(), m.end(), old_uid, new_uid))
    return matches


def replace_guids(xml_text, guid_map):
    """
    Возвращает xml_text, где все old_uid из dict заменены на новые.
    """
    if not guid_map:
        return xml_text
    keys = sorted(guid_map, key=len, reverse=True)
    pattern = re.compile('|'.join(map(re.escape, keys)))
    return pattern.sub(lambda m: guid_map[m.group(0)], xml_text)
