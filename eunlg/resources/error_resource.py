from typing import Dict

ERRORS: Dict[str, Dict[str, str]] = {
    "fi": {
        "no-messages-for-selection": "<p>Valinnastasi ei osata kirjoittaa uutista.</p>",
        "general-error": "<p>Jotain meni vikaan. Yritäthän hetken kuluttua uudelleen.</p>",
        "no-template": "[<i>Haluaisin ilmaista jotain tässä mutten osaa</i>]",
    },
    "en": {
        "no-messages-for-selection": "<p>We are unable to write an article on your selection.</p>",
        "general-error": "<p>Something went wrong. Please try again later.</p>",
        "no-template": "[<i>I don't know how to express my thoughts here</i>]",
    },
}
