"""
Модуль для генерации графиков статистики через matplotlib.
"""

import io
from typing import List, Dict, Any
import matplotlib
matplotlib.use('Agg')  # Используем backend без GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import pytz
from src.config import config
from src.logger import logger

# Настройка стиля графиков
try:
    # Пробуем использовать современный стиль seaborn
    if 'seaborn-v0_8-darkgrid' in plt.style.available:
        plt.style.use('seaborn-v0_8-darkgrid')
    elif 'seaborn-darkgrid' in plt.style.available:
        plt.style.use('seaborn-darkgrid')
    else:
        plt.style.use('default')
except:
    plt.style.use('default')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9


def create_hours_chart(stats_data: List[Dict[str, Any]], period_label: str) -> io.BytesIO:
    """
    Создает столбчатый график активности по часам.
    
    Args:
        stats_data: Список словарей с полями hour (0-23) и count
        period_label: Подпись периода для заголовка
    
    Returns:
        BytesIO: Изображение графика в байтах
    """
    hours = [item['hour'] for item in stats_data]
    counts = [item['count'] for item in stats_data]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(hours, counts, color='#4CAF50', alpha=0.7, edgecolor='#2E7D32', linewidth=1.5)
    
    # Подсветка максимального значения
    max_idx = counts.index(max(counts))
    bars[max_idx].set_color('#FF9800')
    bars[max_idx].set_alpha(1.0)
    
    ax.set_xlabel('Час дня', fontweight='bold')
    ax.set_ylabel('Количество пересылок', fontweight='bold')
    ax.set_title(f'📊 Активность по часам за {period_label}', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(range(24))
    ax.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(bottom=0)
    
    # Добавляем значения на столбцы
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf


def create_weekdays_chart(stats_data: List[Dict[str, Any]], period_label: str) -> io.BytesIO:
    """
    Создает столбчатый график активности по дням недели.
    
    Args:
        stats_data: Список словарей с полями weekday (0-6) и count
        period_label: Подпись периода для заголовка
    
    Returns:
        BytesIO: Изображение графика в байтах
    """
    weekday_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    weekdays = [item['weekday'] for item in stats_data]
    counts = [item['count'] for item in stats_data]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(weekday_names, counts, color='#2196F3', alpha=0.7, edgecolor='#1565C0', linewidth=1.5)
    
    # Подсветка максимального значения
    max_idx = counts.index(max(counts))
    bars[max_idx].set_color('#FF9800')
    bars[max_idx].set_alpha(1.0)
    
    ax.set_xlabel('День недели', fontweight='bold')
    ax.set_ylabel('Количество пересылок', fontweight='bold')
    ax.set_title(f'📊 Активность по дням недели за {period_label}', fontsize=14, fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(bottom=0)
    
    # Добавляем значения на столбцы
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf


def create_days_chart(stats_data: List[Dict[str, Any]], month_name: str, year: int) -> io.BytesIO:
    """
    Создает столбчатый график активности по дням месяца.
    
    Args:
        stats_data: Список словарей с полями day и count
        month_name: Название месяца
        year: Год
    
    Returns:
        BytesIO: Изображение графика в байтах
    """
    days = [item['day'] for item in stats_data]
    counts = [item['count'] for item in stats_data]
    
    fig, ax = plt.subplots(figsize=(14, 6))
    bars = ax.bar(days, counts, color='#9C27B0', alpha=0.7, edgecolor='#6A1B9A', linewidth=1.5)
    
    # Подсветка максимального значения
    if max(counts) > 0:
        max_idx = counts.index(max(counts))
        bars[max_idx].set_color('#FF9800')
        bars[max_idx].set_alpha(1.0)
    
    ax.set_xlabel('День месяца', fontweight='bold')
    ax.set_ylabel('Количество пересылок', fontweight='bold')
    ax.set_title(f'📊 Активность по дням: {month_name} {year}', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(days[::max(1, len(days)//20)])  # Показываем каждый N-й день для читаемости
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(bottom=0)
    
    # Добавляем значения на столбцы (только для ненулевых значений)
    for i, bar in enumerate(bars):
        height = bar.get_height()
        if height > 0 and i % max(1, len(days)//15) == 0:  # Показываем только часть значений
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=7)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf


def create_months_chart(stats_data: List[Dict[str, Any]], year: int) -> io.BytesIO:
    """
    Создает столбчатый график активности по месяцам года.
    
    Args:
        stats_data: Список словарей с полями month (1-12) и count
        year: Год
    
    Returns:
        BytesIO: Изображение графика в байтах
    """
    month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 
                   'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
    
    # Создаем полный список месяцев с нулями для пропущенных
    month_counts = {item['month']: item['count'] for item in stats_data}
    counts = [month_counts.get(m, 0) for m in range(1, 13)]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(month_names, counts, color='#F44336', alpha=0.7, edgecolor='#C62828', linewidth=1.5)
    
    # Подсветка максимального значения
    if max(counts) > 0:
        max_idx = counts.index(max(counts))
        bars[max_idx].set_color('#FF9800')
        bars[max_idx].set_alpha(1.0)
    
    ax.set_xlabel('Месяц', fontweight='bold')
    ax.set_ylabel('Количество пересылок', fontweight='bold')
    ax.set_title(f'📊 Активность по месяцам: {year} год', fontsize=14, fontweight='bold', pad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(bottom=0)
    
    # Добавляем значения на столбцы
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf


def get_month_name(month_number: int) -> str:
    """
    Возвращает название месяца на русском языке.
    
    Args:
        month_number: Номер месяца (1-12)
    
    Returns:
        str: Название месяца
    """
    month_names = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    return month_names.get(month_number, f'Месяц {month_number}')


def get_weekday_name(weekday: int) -> str:
    """
    Возвращает название дня недели на русском языке.
    
    Args:
        weekday: Номер дня недели (0=понедельник, 6=воскресенье)
    
    Returns:
        str: Название дня недели
    """
    weekday_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 
                     'Пятница', 'Суббота', 'Воскресенье']
    return weekday_names[weekday] if 0 <= weekday < 7 else f'День {weekday}'
