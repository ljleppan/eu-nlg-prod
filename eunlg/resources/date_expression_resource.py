from typing import Dict, List, Union

Val = Union[str, List[str]]

ENGLISH: Dict[str, Union[Val, Dict[str, Val]]] = {
    "month": {
        "01": "January",
        "02": "February",
        "03": "March",
        "04": "April",
        "05": "May",
        "06": "June",
        "07": "July",
        "08": "August",
        "09": "September",
        "10": "October",
        "11": "November",
        "12": "December",
        "reference_options": "the same month",
    },
    "year": {"reference_options": "the same year"},
    "month-expression": "{month}",
    "month-year-expression": "{month} {year}",
    "year-expression": "{year}",
}

GERMAN: Dict[str, Union[Val, Dict[str, Val]]] = {
    "month": {
        "01": "Januar",
        "02": "Februar",
        "03": "März",
        "04": "April",
        "05": "Mai",
        "06": "Juni",
        "07": "Juli",
        "08": "August",
        "09": "September",
        "10": "Oktober",
        "11": "November",
        "12": "Dezember",
        "reference_options": ["auch im selben Monat", "gleichzeitich"],
    },
    "year": {"reference_options": ["auch im selben Jahr", "gleichzeitich"]},
    "month-expression": "{month}",
    "month-year-expression": "{month} {year}",
    "year-expression": "Jahr {year}",
}

CROATIAN: Dict[str, Union[Val, Dict[str, Val]]] = {
    "month": {
        "01": "siječanj",
        "02": "veljača",
        "03": "ožujak",
        "04": "travanj",
        "05": "svibanj",
        "06": "lipanj",
        "07": "srpanj",
        "08": "kolovoz",
        "09": "rujan",
        "10": "listopad",
        "11": "studeni",
        "12": "prosinac",
        "reference_options": ["tijekom mjeseca", "također", "u isto vrijeme"],
    },
    "year": {"reference_options": ["u istoj godini", "također tijekom iste godine", "također"]},
    "month-expression": "{month}",
    "month-year-expression": "za {month} mjesec {year}. godine",
    "year-expression": "{year}. godine",
}

FINNISH: Dict[str, Union[Val, Dict[str, Val]]] = {
    "month": {
        "01": "tammikuu",
        "02": "helmikuu",
        "03": "maaliskuu",
        "04": "huhtikuu",
        "05": "toukokuu",
        "06": "kesäkuu",
        "07": "heinäkuu",
        "08": "elokuu",
        "09": "syyskuu",
        "10": "lokakuu",
        "11": "marraskuu",
        "12": "joulukuu",
        "reference_options": ["kyseisessä kuussa", "samaan aikaan"],
    },
    "year": {"reference_options": ["samana vuonna", "myös samana vuonna"]},
    "month-expression": "{month}",
    "month-year-expression": "{month} {year}",
    "year-expression": "vuonna {year}",
}

RUSSIAN: Dict[str, Union[Val, Dict[str, Val]]] = {
    "month": {
        "01": "Январь",
        "02": "Февраль",
        "03": "Март",
        "04": "Апрель",
        "05": "Май",
        "06": "Июнь",
        "07": "Июль",
        "08": "Август",
        "09": "Сентябрь",
        "10": "Октябрь",
        "11": "Ноябрь",
        "12": "Декабрь",
        "reference_options": "тот же месяц",
    },
    "year": {"reference_options": "тот же год"},
    "month-expression": "{month}",
    "month-year-expression": "{month} {year}",
    "year-expression": "{year}",
}

SLOVENIAN: Dict[str, Union[Val, Dict[str, Val]]] = {
    "month": {
        "01": "Januar",
        "02": "Februar",
        "03": "Marec",
        "04": "April",
        "05": "Maj",
        "06": "Junij",
        "07": "Julij",
        "08": "Avgust",
        "09": "September",
        "10": "Oktober",
        "11": "November",
        "12": "December",
        "reference_options": "isti mesec",
    },
    "year": {"reference_options": "isto leto"},
    "month-expression": "{month}",
    "month-year-expression": "{month} {year}",
    "year-expression": "{year}",
}
