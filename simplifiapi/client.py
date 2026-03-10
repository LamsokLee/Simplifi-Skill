import logging
import requests
from urllib.parse import urljoin

from simplifiapi.login.auth import (
    get_token as _login_get_token,
    load_cached_token,
    save_cached_token,
    verify_token as _login_verify_token,
)

logger = logging.getLogger("simplifiapi")

SIMPLIFI_ENDPOINT = "https://services.quicken.com"


class Client():

    def __init__(self):
        self.session = requests.Session()

    def get_token(self, email, password):
        return _login_get_token(self.session, email, password)

    def verify_token(self, token) -> bool:
        return _login_verify_token(self.session, token)

    def _unpaginate(self, path: str, **kargs):
        nextLink = path
        data = []
        while nextLink:
            logger.warn("Fetching {}".format(nextLink))
            r = self.session.get(url=urljoin(
                SIMPLIFI_ENDPOINT, nextLink), **kargs)
            r.raise_for_status()
            data.extend(r.json()["resources"])
            nextLink = r.json().get("metaData", {}).get("nextLink")
        return data

    def get_datasets(self, limit: int = 1000):
        return self._unpaginate(path="/datasets",
                                params={
                                    "limit": limit,
                                })

    def get_accounts(self, datasetId: str):
        return self._unpaginate(path="/accounts",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_transactions(self, datasetId: str):
        return self._unpaginate(path="/transactions",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_tags(self, datasetId: str):
        return self._unpaginate(path="/tags",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_categories(self, datasetId: str):
        return self._unpaginate(path="/categories",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })
