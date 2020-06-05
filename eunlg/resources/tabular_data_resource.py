from abc import ABC


class TabularDataResource(ABC):
    def __init__(self, supported_languages, supported_data):
        self.supported_languages = supported_languages
        self.supported_data = supported_data

    def supports(self, language: str, data: str):
        return (language.lower() == "any" or language.lower() in self.supported_languages) and (
            data.lower() == "any" or data.lower() in self.supported_data
        )
