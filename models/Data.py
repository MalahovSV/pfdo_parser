"""
Читает логин/пароль/сайт из файла data.
Формат файла — три строки:
    логин
    пароль
    URL сайта
"""

from pathlib import Path


class Data:
    def __init__(self, data_path="./data"):
        self.path = Path(data_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Файл data не найден: {self.path}")

        lines = [
            line.strip()
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        if len(lines) < 3:
            raise ValueError(
                f"Файл {self.path} должен содержать 3 строки: "
                f"логин, пароль, URL. Найдено: {len(lines)}"
            )

        self.login = lines[0]
        self.password = lines[1]
        self.site = lines[2]