import markdown
import os
import sys
import re

print("=== generate_help.py: START ===")
print("Current directory:", os.getcwd())
print("Files in current directory:", os.listdir())
print("sys.executable:", sys.executable)

def generate_help():
    """Преобразует README.md в help.html с стилями и работающими ссылками."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if not os.path.exists(readme_path):
        print("README.md not found")
        return

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Преобразуем Markdown в HTML
    md = markdown.Markdown(extensions=['extra'])
    html_body = md.convert(content)

    # Вручную добавляем id к заголовкам (если их нет)
    # Ищем заголовки h1, h2, h3 без id
    def add_id_to_headers(html):
        # Сопоставляем заголовки с текстом
        # Для простоты сделаем id из текста, убирая эмодзи и спецсимволы
        def slugify(text):
            # Убираем эмодзи и специальные символы
            text = re.sub(r'[^\w\s\-]', '', text).strip()
            # Заменяем пробелы на дефисы
            return text.lower().replace(' ', '-')

        # Используем функцию обратного вызова для замены
        def replace_header(match):
            tag = match.group(1)  # h1, h2, h3
            text = match.group(2)  # текст заголовка
            # Извлекаем существующий id, если есть
            id_match = re.search(r'id="([^"]+)"', match.group(0))
            if id_match:
                return match.group(0)  # уже есть id, не меняем
            # Генерируем id из текста
            new_id = slugify(text)
            # Вставляем id в открывающий тег
            return f'<{tag} id="{new_id}">{text}</{tag}>'

        # Регулярное выражение для заголовков без id
        pattern = r'<(h[1-6])>(.*?)</\1>'
        html = re.sub(pattern, replace_header, html)
        return html

    html_body = add_id_to_headers(html_body)

    # CSS стили
    css = """
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.5;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f7fa;
            color: #2c3e50;
        }
        h1, h2, h3 {
            color: #2c3e50;
            border-bottom: 2px solid #ddd;
            padding-bottom: 5px;
        }
        h1 { text-align: center; font-size: 2em; }
        .badge {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-right: 5px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }
        th { background: #ecf0f1; }
        details {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
        }
        summary { font-weight: bold; cursor: pointer; }
        code {
            background: #eee;
            padding: 2px 4px;
            border-radius: 3px;
        }
        .footer {
            text-align: center;
            font-size: 0.9em;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ccc;
        }
        a {
            color: #2980b9;
            text-decoration: none;
        }
        a:hover { text-decoration: underline; }
    </style>
    """

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Справка - Калькулятор коммуналки</title>
    {css}
</head>
<body>
    {html_body}
    <div class="footer">
        <p>Справка сгенерирована автоматически из README.md</p>
    </div>
</body>
</html>
    """

    help_path = os.path.join(os.path.dirname(__file__), 'help.html')
    with open(help_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"help.html generated from README.md")

if __name__ == "__main__":
    generate_help()