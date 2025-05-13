
import enum

class CountriesCapitals(str, enum.Enum):
    LONDON = "london"
    BERLIN = "berlin"
    PARIS = "paris"
    KYIV  = "kyiv"

# capitals_options_list = []
# for member in CountriesCapitals:
#     capitals_options_list.append({
#         "value": member.value,          # Например, "london"
#         "label": member.name.title()    # Например, "London" (первая буква заглавная)
#                                         # или member.value.title() если значения уже "красивые"
#                                         # или любая другая логика для получения "label"
#     })


class UserRole(str, enum.Enum): # Используем строковый Enum для удобства
    USER = "user"
    ADMIN = "admin"
