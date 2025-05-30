import csv
import re
import uuid
import os

# Запрашиваем путь к xml-файлу у пользователя (по умолчанию input.xml)
user_input = input(
    'Введите имя или путь к XML-файлу (по умолчанию input.xml): ').strip()
input_xml = user_input if user_input else "input.xml"

csv_file = "uids.csv"

if not os.path.isfile(input_xml):
    print(f"Ошибка: файл {input_xml} не найден.")
    exit(1)

# Формирование имени итогового файла
base, ext = os.path.splitext(input_xml)
output_file = f"{base}_output{ext}"

# === ВАЖНО: delimiter=';' для поддержки вашего формата ===
guid_map = {}
with open(csv_file, 'r', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=';')
    # Можно удалить после проверки
    print("Поля, определённые в CSV:", reader.fieldnames)
    for row in reader:
        old_uid = row['old_uid']
        new_uid = row['new_uid'].strip() if 'new_uid' in row else ""
        if not new_uid:
            new_uid = str(uuid.uuid4())
        guid_map[old_uid] = new_uid

# Читаем xml-файл целиком
with open(input_xml, 'r', encoding='utf-8') as xmlfile:
    xml_text = xmlfile.read()

# Замена


def replace_guids(text, replacements):
    if not replacements:
        return text
    keys = sorted(replacements, key=len, reverse=True)
    pattern = re.compile('|'.join(map(re.escape, keys)))
    return pattern.sub(lambda m: replacements[m.group(0)], text)


result_text = replace_guids(xml_text, guid_map)

# Сохраняем результат с новым именем
with open(output_file, 'w', encoding='utf-8') as outfile:
    outfile.write(result_text)

print(f'Замена завершена. Итоговый файл сохранён как: {output_file}')
