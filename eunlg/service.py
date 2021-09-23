import gzip
import logging
import os
import pickle
from collections import defaultdict
from pathlib import Path
from random import randint
from typing import Callable, Dict, List, Optional, Tuple, TypeVar

from core.aggregator import Aggregator
from core.datastore import DataFrameStore
from core.models import Template
from core.morphological_realizer import MorphologicalRealizer
from core.pipeline import LanguageSplitComponent, NLGPipeline
from core.realize_slots import SlotRealizer, SlotRealizerComponent
from core.registry import Registry
from core.surface_realizer import BodyHTMLSurfaceRealizer, HeadlineHTMLSurfaceRealizer
from core.template_reader import read_templates
from core.template_selector import TemplateSelector
from croatian_simple_morpological_realizer import CroatianSimpleMorphologicalRealizer
from english_uralicNLP_morphological_realizer import EnglishUralicNLPMorphologicalRealizer
from russian_morphological_realizer import RussianMorphologicalRealizer
from eu_context_sim_document_planner import EUContextSimHeadlineDocumentPlanner, EUContextSimBodyDocumentPlanner
from eu_date_realizer import CroatianEUDateRealizer, EnglishEUDateRealizer, FinnishEUDateRealizer, GermanEUDateRealizer, RussianEUDateRealizer, EstonianEUDateRealizer
from eu_document_planner import EUBodyDocumentPlanner, EUHeadlineDocumentPlanner
from eu_early_stop_document_planner import EUEarlyStopHeadlineDocumentPlanner, EUEarlyStopBodyDocumentPlanner
from eu_importance_allocator import EUImportanceSelector
from eu_message_generator import EUMessageGenerator, NoMessagesForSelectionException
from eu_named_entity_resolver import EUEntityNameResolver
from eu_newsworthiness_only_document_planner import EUScoreHeadlineDocumentPlanner, EUScoreBodyDocumentPlanner
from eu_number_realizer import EUNumberRealizer
from eu_random_document_planner import EURandomHeadlineDocumentPlanner, EURandomBodyDocumentPlanner
from eu_topic_sim_document_planner import EUTopicSimHeadlineDocumentPlanner, EUTopicSimBodyDocumentPlanner
from finnish_uralicNLP_morphological_realizer import FinnishUralicNLPMorphologicalRealizer
from resources.conjunctions_resource import CONJUNCTIONS
from resources.cphi_croatian_resource import CPHICroatianResource
from resources.cphi_english_resource import CPHIEnglishResource
from resources.cphi_finnish_resource import CPHIFinnishResource
from resources.cphi_russian_resource import CPHIRussianResource
from resources.cphi_estonian_resource import CPHIEstonianResource
from resources.env_english_resource import ENVEnglishResource
from resources.env_finnish_resource import ENVFinnishResource
from resources.error_resource import ERRORS
from resources.health_cost_english_resource import HealthCostEnglishResource
from resources.health_cost_finnish_resource import HealthCostFinnishResource
from resources.health_funding_english_resource import HealthFundingEnglishResource
from resources.health_funding_finnish_resource import HealthFundingFinnishResource

log = logging.getLogger(__name__)


class EUNlgService:
    def __init__(
        self,
        random_seed: Optional[int] = None,
        force_cache_refresh: bool = False,
        nomorphi: bool = False,
        planner: str = "full",
    ) -> None:
        """
        :param random_seed: seed for random number generation, for repeatability
        :param force_cache_refresh:
        :param nomorphi: don't load Omorphi for morphological generation. This removes the dependency on Omorphi,
            so allows easier setup, but means that no morphological inflection will be performed on the output,
            which is generally a very bad thing for the full pipeline
        """

        # New registry and result importer
        self.registry = Registry()

        # DataSets
        DATA_ROOT = Path(__file__).parent.absolute() / ".." / "data"

        self.datasets = [
            "cphi",
            "health_cost",
            "health_funding",
        ]
        for dataset in self.datasets:
            cache_path: Path = (DATA_ROOT / "{}.cache".format(dataset)).absolute()
            if not cache_path.exists():
                raise IOError("No cached dataset found at {}. Datasets must be generated before startup.")
            self.registry.register("{}-data".format(dataset), DataFrameStore(str(cache_path)))

        # Resources
        self.resources = [
            CPHIEnglishResource(),
            CPHIFinnishResource(),
            CPHICroatianResource(),
            CPHIRussianResource(),
            CPHIEstonianResource(),
            ENVEnglishResource(),
            ENVFinnishResource(),
            HealthCostEnglishResource(),
            HealthCostFinnishResource(),
            HealthFundingEnglishResource(),
            HealthFundingFinnishResource(),
        ]

        # Templates
        self.registry.register("templates", self._load_templates())

        # Slot Realizers:
        realizers: List[SlotRealizerComponent] = []
        for resource in self.resources:
            for realizer in resource.slot_realizer_components():
                realizers.append(realizer(self.registry))
        self.registry.register("slot-realizers", realizers)

        # Language metadata
        self.registry.register("conjunctions", CONJUNCTIONS)
        self.registry.register("errors", ERRORS)

        # PRNG seed
        self._set_seed(seed_val=random_seed)

        def _get_components(headline=False, planner="full"):
            # Put together the list of components
            # This varies depending on whether it's for headlines and which language we are doing stuff in
            yield EUMessageGenerator(expand=True)
            yield EUImportanceSelector()
            if planner == "random":
                yield EURandomHeadlineDocumentPlanner() if headline else EURandomBodyDocumentPlanner()
            elif planner == "score":
                yield EUScoreHeadlineDocumentPlanner() if headline else EUScoreBodyDocumentPlanner()
            elif planner == "earlystop":
                yield EUEarlyStopHeadlineDocumentPlanner() if headline else EUEarlyStopBodyDocumentPlanner()
            elif planner == "topicsim":
                yield EUTopicSimHeadlineDocumentPlanner() if headline else EUTopicSimBodyDocumentPlanner()
            elif planner == "contextsim":
                yield EUContextSimHeadlineDocumentPlanner() if headline else EUContextSimBodyDocumentPlanner()
            elif planner == "full":
                yield EUHeadlineDocumentPlanner() if headline else EUBodyDocumentPlanner()
            else:
                raise ValueError("INCORRECT PLANNER SETTING")
            yield TemplateSelector()
            yield Aggregator()
            yield SlotRealizer()
            yield LanguageSplitComponent(
                {
                    "en": EnglishEUDateRealizer(),
                    "fi": FinnishEUDateRealizer(),
                    "hr": CroatianEUDateRealizer(),
                    "de": GermanEUDateRealizer(),
                    "ru": RussianEUDateRealizer(),
                    "ee": EstonianEUDateRealizer(),
                }
            )
            yield EUEntityNameResolver()
            yield EUNumberRealizer()
            yield MorphologicalRealizer(
                {
                    "en": EnglishUralicNLPMorphologicalRealizer(),
                    "fi": FinnishUralicNLPMorphologicalRealizer(),
                    "hr": CroatianSimpleMorphologicalRealizer(),
                    "ru": RussianMorphologicalRealizer(),
                }
            )
            yield HeadlineHTMLSurfaceRealizer() if headline else BodyHTMLSurfaceRealizer()

        log.info("Configuring Body NLG Pipeline (planner = {})".format(planner))
        self.body_pipeline = NLGPipeline(self.registry, *_get_components(planner=planner))
        self.headline_pipeline = NLGPipeline(self.registry, *_get_components(headline=True, planner=planner))

    T = TypeVar("T")

    def _get_cached_or_compute(
        self, cache: str, compute: Callable[..., T], force_cache_refresh: bool = False, relative_path: bool = True
    ) -> T:  # noqa: F821 -- Needed until https://github.com/PyCQA/pyflakes/issues/427 reaches a release
        if relative_path:
            cache = os.path.abspath(os.path.join(os.path.dirname(__file__), cache))
        if force_cache_refresh:
            log.info("force_cache_refresh is True, deleting previous cache from {}".format(cache))
            if os.path.exists(cache):
                os.remove(cache)
        if not os.path.exists(cache):
            log.info("No cache at {}, computing".format(cache))
            result = compute()
            with gzip.open(cache, "wb") as f:
                pickle.dump(result, f)
            return result
        else:
            log.info("Found cache at {}, decompressing and loading".format(cache))
            with gzip.open(cache, "rb") as f:
                return pickle.load(f)

    def _load_templates(self) -> Dict[str, List[Template]]:
        log.info("Loading templates")
        templates: Dict[str, List[Template]] = defaultdict(list)
        for resource in self.resources:
            for language, new_templates in read_templates(resource.templates)[0].items():
                templates[language].extend(new_templates)

        log.debug("Templates:")
        for lang, lang_templates in templates.items():
            log.debug("\t{}".format(lang))
            for templ in lang_templates:
                log.debug("\t\t{}".format(templ))
        return templates

    def get_locations(self, dataset: str) -> List[str]:
        return list(self.registry.get("{}-data".format(dataset)).all()["location"].unique()) + ["all"]

    def get_datasets(self, language: Optional[str] = None) -> List[str]:
        return list(
            {
                dataset
                for resource in self.resources
                for dataset in resource.supported_data
                if (language is None or resource.supports(language, dataset)) and dataset in self.datasets
            }
        )

    def get_languages(self):
        return list({language for resource in self.resources for language in resource.supported_languages})

    def run_pipeline(self, language: str, dataset: str, location: str, location_type: str) -> Tuple[str, str]:
        log.info("Running headline NLG pipeline")
        try:
            headline_lang = "{}-head".format(language)
            headline = self.headline_pipeline.run((location, location_type, dataset), headline_lang,)
            log.info("Headline pipeline complete")
        except Exception as ex:
            headline = location
            log.error("%s", ex)

        # TODO: Figure out what DATA is supposed to be here?!
        log.info(
            "Running Body NLG pipeline: language={}, dataset={}, location={}, location_type={}".format(
                language, dataset, location, location_type
            )
        )
        try:
            body = self.body_pipeline.run((location, location_type, dataset), language)
            log.info("Body pipeline complete")
        except NoMessagesForSelectionException:
            log.error("User selection returned no messages")
            body = ERRORS.get(language, {}).get(
                "no-messages-for-selection", "Something went wrong. Please try again later",
            )
        except Exception as ex:
            log.error("%s", ex)
            body = ERRORS.get(language, {}).get("general-error", "Something went wrong. Please try again later")

        return headline, body

    def _set_seed(self, seed_val: Optional[int] = None) -> None:
        log.info("Selecting seed for NLG pipeline")
        if not seed_val:
            seed_val = randint(1, 10000000)
            log.info("No preset seed, using random seed {}".format(seed_val))
        else:
            log.info("Using preset seed {}".format(seed_val))
        self.registry.register("seed", seed_val)
