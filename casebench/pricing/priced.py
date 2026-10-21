"""A config with every model priced: a price written in casebench.yaml first, else the lists.

casebench.yaml holds no price unless someone writes one, for a model no list sells
(decision 0069).
"""

from casebench.config import CasebenchConfig
from casebench.judge.config import JudgeConfig
from casebench.pricing.lookup import PriceList, openrouter_url


def _model(model: JudgeConfig, prices: PriceList) -> JudgeConfig:
    if model.price is not None:
        return model
    found = prices.price(model.model, openrouter_url(model.options.get("base_url")))
    return model.model_copy(update={"price": found}) if found else model


def priced(config: CasebenchConfig, prices: PriceList) -> CasebenchConfig:
    agent = [
        m if m.price is not None else m.model_copy(update={"price": prices.price(m.model)})
        for m in config.agent_models
    ]
    extract = config.extract
    if extract is not None:
        extract = extract.model_copy(update={"models": [_model(m, prices) for m in extract.models]})
    return config.model_copy(
        update={
            "judges": [_model(j, prices) for j in config.judges],
            "extract": extract,
            "agent_models": agent,
        }
    )
