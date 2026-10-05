"""Müşteri takip ve ödeme takibi programı. Çalıştırma: python main.py"""
import os

from db import Database
from ui import App


def main():
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "musteri_takip.db")
    App(Database(yol)).mainloop()


if __name__ == "__main__":
    main()
