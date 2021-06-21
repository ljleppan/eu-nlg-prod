from typing import Dict, List, Type

from core.realize_slots import LookupRealizer, RegexRealizer, SlotRealizerComponent
from resources.tabular_data_resource import TabularDataResource

TEMPLATES: str = """
# PRESENT VALUE

ru: [в {time, case=loc2},] [в {location, case=loc2},] {value_type} был(-а) {value} {unit}
ru-head: в {location, case=loc2}, в {time, case=loc2}, {value_type} был(-а) {value} {unit}
| value_type = cphi:.*, value_type != .*:rank.*, value_type != .*:comp_.*

# SINGLE VALUE COMP EU

ru: [в {time, case=loc2},] [в {location, case=loc2},] {value_type} был(-а) {value} {unit} больше, чем в среднем по ЕС
ru-head: в {location, case=loc2}, в {time, case=loc2}, {value_type} был(-а) {value} {unit} выше среднего по ЕС 
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value > 0

ru: [в {time, case=loc2},] [в {location, case=loc2},] {value_type} был(-а) {value, abs} {unit} меньше, чем в среднем по ЕС
ru-head: в {location, case=loc2}, в {time, case=loc2}, {value_type} на {value, abs} {unit} ниже среднего по ЕС 
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value < 0

ru: [в {time, case=loc2},] [в {location, case=loc2},] {value_type} был(-а) таким же, как в среднем по ЕС
ru-head: в {location, case=loc2}, в {time, case=loc2}, {value_type} был(-а) таким же, как в среднем по ЕС
| value_type = cphi:.*:comp_eu, value_type != .*:rank.*, value = 0.0

# SINGLE VALUE COMP US

ru: [в {time, case=loc2},] [в {location, case=loc2},] {value_type} был(-а) {value} {unit} больше чем в США
ru-head: в {location, case=loc2}, в {time, case=loc2}, {value_type} на {value} {unit} больше США
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value > 0

ru: [в {time, case=loc2},] [в {location, case=loc2},] {value_type} был(-а) {value, abs} {unit} меньше чем в США
ru-head: in {location, case=loc2}, in {time, case=loc2}, {value_type} на {value, abs} {unit} меньше США
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value < 0

ru: [в {time, case=loc2},] [в {location, case=loc2},] {value_type} был(-а) таким же, как в США 
ru-head: в {location, case=loc2}, в {time, case=loc2}, {value_type} был(-а) таким же, как в США
| value_type = cphi:.*:comp_us, value_type != .*:rank.*, value = 0.0

# RANK

ru: [в {time, case=loc2},] {location, case=loc2} имел(-а) {value, ord} самый высокий {value_type} во всех наблюдаемых странах
ru: [в {time, case=loc2},] {location, case=loc2} имел(-а) {value, ord} самый высокое значение во всех наблюдаемых странах
ru-head: в {time, case=loc2}, {location, case=gen} {value, ord} {value_type} самое высокое
| value_type = cphi:.*:rank.*, value_type != .*rank_reverse.*

# RANK_REVERSE

ru: [в {time, case=loc2},] {location, case=loc2} имел(-а) {value, ord} самый низкий {value_type} во всех наблюдаемых странах
ru: [в {time, case=loc2}, ]{location, case=loc2} имел(-а) {value, ord} самое низкое для этого значение во всех наблюдаемых странах
ru-head: в {time, case=loc2}, {location, case=gen} {value, ord} {value_type} самое низкое
| value_type = cphi:.*:rank_reverse.*
"""

INDEX_CATEGORIES: Dict[str, str] = {
    "hicp2015": "согласованного индекса потребительских цен",  # harmonized consumer price index (2015=100)
    "rt1": "ежемесячный темп роста",  # growth rate on previous period (t/t-1)
    "rt12": "годовой темп роста",  # growth rate (t/t-12)
    "cp-hi00": "'все элементы'",
    "cp-hi01": "'еда и безалкогольные напитки'",
    "cp-hi02": "'алкогольные напитки и табак'",
    "cp-hi03": "'одежда и обувь'",
    "cp-hi04": "'жилье, вода, электричество, газ и другие виды топлива'",
    "cp-hi05": "'мебель, бытовая техника и обслуживание'",
    "cp-hi06": "'здоровье'",
    "cp-hi07": "'транспорт'",
    "cp-hi08": "'общение'",
    "cp-hi09": "'отдых и культура'",
    "cp-hi10": "'образование'",
    "cp-hi11": "'гостиницы, кафе и рестораны'",
    "cp-hi12": "'разные товары и услуги'",
    "cp-hi00xef": "'все товары, кроме энергии, еды, алкоголя и табака'",
    "cp-hi00xtb": "'все товары, кроме табака'",
    "cp-hie": "'энергия'",
    "cp-hif": "'еда'",
    "cp-hifu": "'необработанная еда'",
    "cp-hig": "'всего товаров'",
    "cp-hiig": "'промышленные товары'",
    "cp-his": "'всего услуг'",
    "cp-hiigxe": "'неэнергетические промышленные товары'",
    "cp-hi00xe": "'все элементы, кроме энергии'",
    "cp-hi00xefu": "'все товары, кроме энергоносителей и необработанных продуктов'",
    "cp-hi00xes": "'все товары, кроме энергии и сезонной еды'",
}


class CPHIRussianResource(TabularDataResource):
    def __init__(self):
        super().__init__(["ru"], ["cphi"])
        self.templates = TEMPLATES
        self.partials = INDEX_CATEGORIES

    def slot_realizer_components(self) -> List[Type[SlotRealizerComponent]]:
        return [
            RussianCphiRawRealizer,
            RussianCphiChangeRealizer,
            RussianCphiCategoryRealizer,
            RussianUnitCphiPercentageRealizer,
            RussianUnitCphiPointsRealizer,
        ]


MAYBE_RANK_OR_COMP = ":?(rank|rank_reverse|comp_eu|comp_us)?"


class RussianCphiRawRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(registry, "ru", r"^cphi:([^:]*):([^:]*)" + MAYBE_RANK_OR_COMP + "$", "{} для категории {}")


class RussianCphiChangeRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "ru",
            r"^cphi:([^:]*):([^:]*):(rt12?)" + MAYBE_RANK_OR_COMP + "$",
            "{2} {0} для категории {1}",
        )


class RussianUnitCphiPercentageRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "ru",
            r"^\[UNIT:cphi:.*\]$",
            "процентные пункты",
            slot_requirements=lambda slot: "rt1" in slot.value.split(":") or "rt12" in slot.value.split(":"),
        )


class RussianUnitCphiPointsRealizer(RegexRealizer):
    def __init__(self, registry):
        super().__init__(
            registry,
            "ru",
            r"^\[UNIT:cphi:.*\]$",
            "пункты",
            slot_requirements=lambda slot: "rt1" not in slot.value.split(":") and "rt12" not in slot.value.split(":"),
        )


class RussianCphiCategoryRealizer(LookupRealizer):
    def __init__(self, registry):
        super().__init__(registry, "ru", INDEX_CATEGORIES)
