"""Müşteri takip ve ödeme takibi programı. Çalıştırma: python main.py"""
import os

from config import data_dir
from db import Database
from ui import App


def main():
    yol = os.path.join(data_dir(), "musteri_takip.db")
    App(Database(yol)).mainloop()


if __name__ == "__main__":
    main()
