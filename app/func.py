import random                                           # Для рандомизации
from typing import Union                                # Для валидации

# Загружаем данные из файлов
def load_data(filename):
    with open(filename, 'r', encoding='UTF-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]
    
# Функция для загрузки данных с разными разделителями
def load_jokes(filename):
    with open(filename, 'r', encoding='UTF-8') as f:
        content = f.read().strip()
        # Пробуем разные разделители
        if '%%%' in content:
            return [joke.strip() for joke in content.split('%%%') if joke.strip()]
        else:
            return [joke.strip() for joke in content.split('\n\n') if joke.strip()]
        
# Функция рандомизации
def randomizing(min: int, max: int) -> tuple[list[int], int]:
    # Проверка на минимальный диапазон
    if max - min + 1 < 2:
        raise ValueError("Диапазон должен содержать как минимум 2 числа")
    
    numbers = list(range(min, max + 1))                         # Список кандидатов из диапазона и массив для выбывших кандидатов
    eliminated = []
    
    
    while len(numbers) > 2:                                                     # Этап 1: Рандомизация, пока чисел больше 2
        shuffled = random.sample(numbers, len(numbers))                             # Генерируем случайную перестановку всех чисел
        eliminated.append(shuffled[-1])                                             # Последнее число выбывает и записывается
        numbers.remove(shuffled[-1])
    
    first_num, second_num = numbers                                             # Этап 2: Битва двух чисел
    winner = None                                                                   # Число-победитель
    fn_score, sn_score = 0, 0                                                       # Счетчики баллов
    
    while winner is None:
        batch = [random.choice(numbers) for _ in range(50)]                         # Генерируем 50 случайных чисел из оставшихся двух
        
        counts = {first_num: 0, second_num: 0}                                      # Счётчики повторений
        last_scored = None                                                          # Последнее число, получившее балл
        current_ignore = None                                                       # Число, которое временно игнорируем

        for num in batch:
            if current_ignore is not None:                                          # Пропускаем игнорируемое число
                if num == current_ignore:
                    continue
                else:
                    current_ignore = None
            
            counts[num] += 1                                                        # Увеличиваем счётчик для текущего числа
            
            if counts[num] >= 3 and num != last_scored:                             # Проверяем начисление балла
                if num == first_num:
                    fn_score += 1
                else:
                    sn_score += 1
                
                counts[num] = 0                                                     # Сбрасываем и блокируем
                last_scored = num
                current_ignore = num
                
                if fn_score >= 3:                                                   # Проверяем победителя
                    winner = first_num
                    break
                if sn_score >= 3:
                    winner = second_num
                    break
        
        # Если после 50 чисел нет победителя, генерируем новую партию
    
    return eliminated, winner           # Возвращаем выбывших кандидатов и победителя

# Валидация числа в рандомайзере
def validate_number(input_str: str) -> int | None:
    try:                                    
        num = int(input_str)            # Проверяет, является ли строка положительным целым числом
        return num if num >= 0 else None
    except (ValueError, TypeError):
        return None