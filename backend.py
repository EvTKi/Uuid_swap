import csv
import re
import uuid
import os


def load_guid_map(csv_path):
    """
    Загружает соответствия из CSV и возвращает dict {old_uid: new_uid}, 
    а также список автоматически сгенерированных new_uid для дальнейшей записи.
    """
    guid_map = {}
    gen_rows = []  # [(row_num, old_uid, new_uid)]
    all_rows = []  # [(old_uid, new_uid)] для перезаписи
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            fieldnames = reader.fieldnames
            for idx, row in enumerate(reader):
                old_uid = row.get('old_uid', '').strip()
                new_uid = row.get('new_uid', '').strip()
                if old_uid:
                    if not new_uid:
                        new_uid = str(uuid.uuid4())
                        gen_rows.append((idx, old_uid, new_uid))
                    guid_map[old_uid] = new_uid
                    all_rows.append((old_uid, new_uid))
    except Exception as e:
        raise RuntimeError(f'Ошибка чтения CSV: {e}')
    return guid_map, gen_rows, all_rows, fieldnames


def write_guid_map(csv_path, all_rows, fieldnames):
    """
    Перезаписывает CSV-файл, подставляя сгенерированные new_uid.
    """
    try:
        with open(csv_path, "w", newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            if not fieldnames:
                fieldnames = ['old_uid', 'new_uid']
            writer.writerow(fieldnames)
            for old_uid, new_uid in all_rows:
                writer.writerow([old_uid, new_uid])
    except Exception as e:
        raise RuntimeError(f'Ошибка обновления CSV: {e}')

# Остальные функции не меняются


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
    if not guid_map:
        return xml_text
    keys = sorted(guid_map, key=len, reverse=True)
    pattern = re.compile('|'.join(map(re.escape, keys)))
    return pattern.sub(lambda m: guid_map[m.group(0)], xml_text)
