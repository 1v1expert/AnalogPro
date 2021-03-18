def _rev_dict(choices):
    return {v: k for k, v in choices}


def _dict(choices):
    return {k: v for k, v in choices}




HARD          = 'hrd'
SOFT          = 'sft'
RECALCULATION = 'rcl'
RELATION      = 'rlt'
PRICE         = 'prc'

TYPES = (
    (HARD,          'жесткий'),
    (SOFT,          'мягкий'),
    (RECALCULATION, 'пересчет'),
    (RELATION,      'взаимосвязь'),
    (PRICE,         'цена')
)
TYPES_REV_DICT = _rev_dict(TYPES)
TYPES_DICT = _dict(TYPES)

UNITS = (
    ('mm', 'мм'),
    ('cm', 'см'),
    ('m', 'м'),
    ('km', 'км'),
    ('g', 'гр'),
    ('kg', 'кг'),
    ('tonne', 'т')
)

TYPES_SEARCH = (
    ('nearest', 'Ближайший'),
    ('min', 'Минимальный'),
    ('max', 'Максимальный'),
    ('closest_min', 'Ближайшее минимальное'),
    ('closest_max', 'Ближайшее максимальное'))

TYPES_FILE = (
    ('import', 'Импорт базы'),
    ('search', 'Поиск'),
    ('result_search', 'Результат поиска'),
    ('export', 'Экспорт данных')
)
