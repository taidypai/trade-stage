import os
import sys
sys.path.append(r"C:\Users\Вадим\Documents\python\trade-brain-main")
import config

class Environment:
    def __init__(self):
        self.directory = 'C:/QUIK_DATA/'
        self.files = config.FILES
    def setup_environment(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory )
            print(f"✓ Создана директория: {self.directory }")
        """Настройка окружения"""
        for file in self.files:
            print(file)
            if not os.path.exists(file):
                with open(file, 'w', encoding='utf-8') as f:
                    f.write("")
                print(f"✓ Создан файл: {file}")
    def clean_environment(self):
        """Настройка окружения"""
        for file in self.files:
            with open(file, 'w', encoding='utf-8') as f:
                f.write("")

settings = Environment()

def environment_main():
    settings.setup_environment()

if __name__ == "__main__":
    main()