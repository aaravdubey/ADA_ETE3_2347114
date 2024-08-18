import asyncio
import json
import random
import string
from typing import List, TypedDict

import httpx
from loguru import logger as log


class LocationData(TypedDict):
    """result dataclass for tripadvisor location data"""

    localizedName: str
    url: str
    HOTELS_URL: str
    ATTRACTIONS_URL: str
    RESTAURANTS_URL: str
    placeType: str
    latitude: float
    longitude: float


async def scrape_location_data(query: str, client: httpx.AsyncClient) -> List[LocationData]:
    log.info(f"scraping location data: {query}")
    payload = [
        {
            "variables": {
                "request": {
                    "query": query,
                    "limit": 10,
                    "scope": "WORLDWIDE",
                    "locale": "en-US",
                    "scopeGeoId": 1,
                    "searchCenter": None,
                    "types": [
                        "LOCATION",
                    ],
                    "locationTypes": [
                        "GEO",
                        "AIRPORT",
                        "ACCOMMODATION",
                        "ATTRACTION",
                        "ATTRACTION_PRODUCT",
                        "EATERY",
                        "NEIGHBORHOOD",
                        "AIRLINE",
                        "SHOPPING",
                        "UNIVERSITY",
                        "GENERAL_HOSPITAL",
                        "PORT",
                        "FERRY",
                        "CORPORATION",
                        "VACATION_RENTAL",
                        "SHIP",
                        "CRUISE_LINE",
                        "CAR_RENTAL_OFFICE",
                    ],
                    "userId": None,
                    "context": {},
                    "enabledFeatures": ["articles"],
                    "includeRecent": True,
                }
            },
            "query": "84b17ed122fbdbd4",
            "extensions": {"preRegisteredQueryId": "84b17ed122fbdbd4"},
        }
    ]

    random_request_id = "".join(
        random.choice(string.ascii_lowercase + string.digits) for i in range(180)
    )
    headers = {
        "X-Requested-By": random_request_id,
        "Referer": "https://www.tripadvisor.com/Hotels",
        "Origin": "https://www.tripadvisor.com",
    }
    result = await client.post(
        url="https://www.tripadvisor.com/data/graphql/ids",
        json=payload,
        headers=headers,
    )
    data = json.loads(result.content)

    # Debugging: print the raw API response
    # log.debug(f"Raw API response: {json.dumps(data, indent=2)}")

    results = data[0]["data"]["Typeahead_autocomplete"]["results"]

    # Safely access 'details' and handle cases where it's missing
    sanitized_results = []
    for r in results:
        details = r.get("details")
        if details:
            sanitized_results.append(details)
        else:
            log.warning(f"Missing 'details' in result: {r}")

    log.info(f"found {len(sanitized_results)} results")
    return sanitized_results

# To avoid being instantly blocked we'll be using request headers that
# mimic Chrome browser on Windows
BASE_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9,en-IN;q=0.8',
    'cache-control': 'max-age=0',
    # 'cookie': 'TASameSite=1; TAUnique=%1%enc%3AS2VcckoBMpjkWWE0EOYFXwpeYGtm89yjVCeQrfyOvOjuSk%2FeFO0ovn5aojuWt%2F0ZNox8JbUSTxk%3D; ext_name=ojplmecpdpgccookcobabopnaifgidhf; TASSK=enc%3AADgp9hPB2EZH%2BG%2FrGuviR%2Fz0M2tI26%2Bka189fC2uttEXwRtO7D7itb6MVmBRjyeKGdZKlS99%2FrM9Atb%2B%2B6O10u8OqOH6gsbaISOcYnUu5PSF4dGFptO9uxrXWnb3F1YgKQ%3D%3D; VRMCID=%1%V1*id.10568*llp.%2F*e.1722363570030; TATrkConsent=eyJvdXQiOiJTT0NJQUxfTUVESUEiLCJpbiI6IkFEVixBTkEsRlVOQ1RJT05BTCJ9; TADCID=fg4MNOwHq-ef7uhfABQCrj-Ib21-TgWwDB4AzTFpg3-g8s66h_g0CWvXLT5871oT4ms3XFF0963pzoSwGI72-3kU9hLiNK6DRrw; TASID=CEA13F869BBD11312FB1D0F50296976D; PAC=ANzuInxr1C7S5OOINagy0h5lm6xlR2WM3TcSR9ZrG1zaVky3O4aSeP59-5R97WWXnKiyt7BBwp9jLlKOpz0VuuKfM3dYPdYoCXKCgrOuRHckvqvilPmE-_JUe8wuGo8opeCJUHg41mH4uZ3cMJFAG5I%3D; SRT=TART_SYNC; TART=%1%enc%3A%2FdIfHPLAZA23RNkD9Zj1QS5tDbD9sFfhxGohbaYH5EFtdmek5ZZ1a53nmqJtCXdvkagyFvowwb0%3D; ServerPool=C; TATravelInfo=V2*A.2*MG.-1*HP.2*FL.3*RS.1; PMC=V2*MS.16*MD.20240817*LD.20240817; G_AUTH2_MIGRATION=informational; OptanonConsent=isGpcEnabled=0&datestamp=Sat+Aug+17+2024+10%3A24%3A48+GMT%2B0530+(India+Standard+Time)&version=202310.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=f3dff3a0-8547-415c-a0ec-72ff33e27b1e&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&AwaitingReconsent=false; TAAUTHEAT=rsTuScUL_9f-LqI_ABQCS_DXENAPSyOjZ55LXtF4ZD9387oMdgaeiJTOCZQ8NjerXG6Wl2B2TRPznYENy1_Ptw7T25YrGxsy8QVhtaxEQKtnR6CLewqsJtqCO3UDfwfC9v148ognBu9Is9HG7L-DDlLYtWYFU-9QN4mSj0Dgty_B8D41BKsE3O-cvrDFzx1KnRfHiTOPbU1oMlPVn0ZeIZ8CV6Yw0K_cbw4; TAUD=LA-1723870420788-1*RDD-1-2024_08_17*LG-74548-2.1.F.*LD-74549-.....; datadome=F7uQ7DG8OR3bq6qJ1ZKjPE9A837cJXAQv_AUTG~cSEAz2EcRi7pM6NQTdE0edtggdSV28423nY4V0B2rIMaKUes0YsGrjgfTXX48rJS1~_VNCS4klpfN72Dze8m0OXm4; AMZN-Token=v2FweIBCUi9GYTRyRVBjRUl2REE2MFpPMjdaREYvZUp4bWRXS3Y4SU4wbEIxb0Fqb1NVQUxPMkRxNFFVYzg4eVhxNGNxQmtWMmkzTUFOUWt0NlJxTXBlWkgrbTMyY0Yyam1KcHR3OWVqOFdWR3pPV28xNU5za00zdXdyQXMwSG5tZkNEYmJrdgFiaXZ4GE1EUjZaKysvdmUrL3ZRVHZ2NzNUcUV3NP8=; __vt=Tb2Wdk1YlzeNJbzrABQCjdMFtf3dS_auw5cMBDN7SS9-kx86OvBqVoi1fUiqnZp-Qvusl6V3zgSPrJlJX-cVwwrwZvXj4CUCd-Q9lAqrPpvSBDHQCcKiU4nM3hHPDKYod-gTv-VjGBjk5uQl3Z6kHXAtTw; ab.storage.deviceId.6e55efa5-e689-47c3-a55b-e6d7515a6c5d=%7B%22g%22%3A%22abc18bac-72a2-cf72-5aef-b5074d0256ca%22%2C%22c%22%3A1721758771004%2C%22l%22%3A1723870527918%7D; ab.storage.userId.6e55efa5-e689-47c3-a55b-e6d7515a6c5d=%7B%22g%22%3A%22MTA%3A8C3DC1FA938CED5E8FD68F02EEBBDEAE%22%2C%22c%22%3A1723870495774%2C%22l%22%3A1723870527919%7D; ab.storage.sessionId.6e55efa5-e689-47c3-a55b-e6d7515a6c5d=%7B%22g%22%3A%22fbda62f6-1f7e-8af5-2a6b-8d9dcdcf49f1%22%2C%22e%22%3A1723870545985%2C%22c%22%3A1723870527917%2C%22l%22%3A1723870530985%7D; TASession=%1%V2ID.CEA13F869BBD11312FB1D0F50296976D*SQ.11*PR.40185%7C*LS.Search*HS.recommended*ES.popularity*DS.5*SAS.popularity*FPS.oldFirst*TS.8C3DC1FA938CED5E8FD68F02EEBBDEAE*FA.1*DF.0*TRA.true',
    'priority': 'u=0, i',
    'sec-ch-device-memory': '8',
    'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Microsoft Edge";v="128"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-full-version-list': '"Chromium";v="128.0.6613.27", "Not;A=Brand";v="24.0.0.0", "Microsoft Edge";v="128.0.2739.22"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
}

cookies = {
    'TASameSite': '1',
    'TAUnique': '%1%enc%3AS2VcckoBMpjkWWE0EOYFXwpeYGtm89yjVCeQrfyOvOjuSk%2FeFO0ovn5aojuWt%2F0ZNox8JbUSTxk%3D',
    'ext_name': 'ojplmecpdpgccookcobabopnaifgidhf',
    'TASSK': 'enc%3AADgp9hPB2EZH%2BG%2FrGuviR%2Fz0M2tI26%2Bka189fC2uttEXwRtO7D7itb6MVmBRjyeKGdZKlS99%2FrM9Atb%2B%2B6O10u8OqOH6gsbaISOcYnUu5PSF4dGFptO9uxrXWnb3F1YgKQ%3D%3D',
    'VRMCID': '%1%V1*id.10568*llp.%2F*e.1722363570030',
    'TATrkConsent': 'eyJvdXQiOiJTT0NJQUxfTUVESUEiLCJpbiI6IkFEVixBTkEsRlVOQ1RJT05BTCJ9',
    'TADCID': 'fg4MNOwHq-ef7uhfABQCrj-Ib21-TgWwDB4AzTFpg3-g8s66h_g0CWvXLT5871oT4ms3XFF0963pzoSwGI72-3kU9hLiNK6DRrw',
    'TASID': 'CEA13F869BBD11312FB1D0F50296976D',
    'PAC': 'ANzuInxr1C7S5OOINagy0h5lm6xlR2WM3TcSR9ZrG1zaVky3O4aSeP59-5R97WWXnKiyt7BBwp9jLlKOpz0VuuKfM3dYPdYoCXKCgrOuRHckvqvilPmE-_JUe8wuGo8opeCJUHg41mH4uZ3cMJFAG5I%3D',
    'SRT': 'TART_SYNC',
    'TART': '%1%enc%3A%2FdIfHPLAZA23RNkD9Zj1QS5tDbD9sFfhxGohbaYH5EFtdmek5ZZ1a53nmqJtCXdvkagyFvowwb0%3D',
    'ServerPool': 'C',
    'TATravelInfo': 'V2*A.2*MG.-1*HP.2*FL.3*RS.1',
    'PMC': 'V2*MS.16*MD.20240817*LD.20240817',
    'G_AUTH2_MIGRATION': 'informational',
    'OptanonConsent': 'isGpcEnabled=0&datestamp=Sat+Aug+17+2024+10%3A24%3A48+GMT%2B0530+(India+Standard+Time)&version=202310.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=f3dff3a0-8547-415c-a0ec-72ff33e27b1e&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&AwaitingReconsent=false',
    'TAAUTHEAT': 'rsTuScUL_9f-LqI_ABQCS_DXENAPSyOjZ55LXtF4ZD9387oMdgaeiJTOCZQ8NjerXG6Wl2B2TRPznYENy1_Ptw7T25YrGxsy8QVhtaxEQKtnR6CLewqsJtqCO3UDfwfC9v148ognBu9Is9HG7L-DDlLYtWYFU-9QN4mSj0Dgty_B8D41BKsE3O-cvrDFzx1KnRfHiTOPbU1oMlPVn0ZeIZ8CV6Yw0K_cbw4',
    'TAUD': 'LA-1723870420788-1*RDD-1-2024_08_17*LG-74548-2.1.F.*LD-74549-.....',
    'datadome': 'F7uQ7DG8OR3bq6qJ1ZKjPE9A837cJXAQv_AUTG~cSEAz2EcRi7pM6NQTdE0edtggdSV28423nY4V0B2rIMaKUes0YsGrjgfTXX48rJS1~_VNCS4klpfN72Dze8m0OXm4',
    'AMZN-Token': 'v2FweIBCUi9GYTRyRVBjRUl2REE2MFpPMjdaREYvZUp4bWRXS3Y4SU4wbEIxb0Fqb1NVQUxPMkRxNFFVYzg4eVhxNGNxQmtWMmkzTUFOUWt0NlJxTXBlWkgrbTMyY0Yyam1KcHR3OWVqOFdWR3pPV28xNU5za00zdXdyQXMwSG5tZkNEYmJrdgFiaXZ4GE1EUjZaKysvdmUrL3ZRVHZ2NzNUcUV3NP8=',
    '__vt': 'Tb2Wdk1YlzeNJbzrABQCjdMFtf3dS_auw5cMBDN7SS9-kx86OvBqVoi1fUiqnZp-Qvusl6V3zgSPrJlJX-cVwwrwZvXj4CUCd-Q9lAqrPpvSBDHQCcKiU4nM3hHPDKYod-gTv-VjGBjk5uQl3Z6kHXAtTw',
    'ab.storage.deviceId.6e55efa5-e689-47c3-a55b-e6d7515a6c5d': '%7B%22g%22%3A%22abc18bac-72a2-cf72-5aef-b5074d0256ca%22%2C%22c%22%3A1721758771004%2C%22l%22%3A1723870527918%7D',
    'ab.storage.userId.6e55efa5-e689-47c3-a55b-e6d7515a6c5d': '%7B%22g%22%3A%22MTA%3A8C3DC1FA938CED5E8FD68F02EEBBDEAE%22%2C%22c%22%3A1723870495774%2C%22l%22%3A1723870527919%7D',
    'ab.storage.sessionId.6e55efa5-e689-47c3-a55b-e6d7515a6c5d': '%7B%22g%22%3A%22fbda62f6-1f7e-8af5-2a6b-8d9dcdcf49f1%22%2C%22e%22%3A1723870545985%2C%22c%22%3A1723870527917%2C%22l%22%3A1723870530985%7D',
    'TASession': '%1%V2ID.CEA13F869BBD11312FB1D0F50296976D*SQ.11*PR.40185%7C*LS.Search*HS.recommended*ES.popularity*DS.5*SAS.popularity*FPS.oldFirst*TS.8C3DC1FA938CED5E8FD68F02EEBBDEAE*FA.1*DF.0*TRA.true',
}

# start HTTP session client with our headers and HTTP2
client = httpx.AsyncClient(
    http2=True,  # http2 connections are significantly less likely to get blocked
    headers=BASE_HEADERS,
    timeout=httpx.Timeout(150.0),
    limits=httpx.Limits(max_connections=5),
    cookies=cookies,
)


async def run():
    result = await scrape_location_data("Malta", client)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(run())