from typing import Optional, List

import requests
from bs4 import BeautifulSoup, Tag
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class Price:
    """A data class representing the price per MWh on a hub at a given time."""
    price: float  # The price per MWh
    timestamp: datetime  # The timestamp of the given price.
    hub: str  # the hub on which the price is settled.


class RealtimeSettlementParser:
    """A parser that extract the realtime settlement information from ERCOT."""

    def __init__(self, url: str = "https://www.ercot.com/content/cdr/html/real_time_spp.html"):
        self.url: str = url  # the URL at which the information is available.
        self.date_format: str = "%m/%d/%Y"  # the format of the date component in the table
        self.time_format: str = "%H%M"  # the format of the time component in the table.

    def get_locations(self) -> List[str]:
        """Gets the list of hubs and Load zones available as a list of strings."""
        table = self._get_table()
        return self._extract_headers(table)[2:]

    def parse_data(self, zone_or_hub: str, start_time: Optional[datetime] = None) -> List[Price]:
        """
        Extracts the price information for the given hub / load zone and on or after the optional datetime.

        :param zone_or_hub: The load zone / hub to use for extracting the price data.
        :param start_time: THe optional start time to use for extracting the price information, if None is provided 15 minutes prior to the method call will be used.

        :return The list of prices on or after the date time for the provided load zone / hub.
        :rtype List[Price]
        """
        if zone_or_hub is None:
            raise ValueError("zone_or_hub parameter must be provided, use get_locations to select the appropriate one.")
        if start_time is None:
            start_time = datetime.now() - timedelta(minutes=15)
        elif not isinstance(start_time, datetime):
            raise ValueError("Invalid start_time argument. Please provide a valid datetime object")

        table = self._get_table()
        rows = table.find_all("tr")

        # get index of the chosen zone
        headers = self._extract_headers(table)

        hub_zone_index = headers.index(zone_or_hub)
        date_index = headers.index("Oper Day")
        time_index = headers.index("Interval Ending")

        result = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                price_datetime = self._create_datetime(cols[date_index].text.strip(), cols[time_index].text.strip())
                price = cols[hub_zone_index].text
                if start_time <= price_datetime:
                    result.append(
                        Price(price=float(price), timestamp=price_datetime, hub=zone_or_hub)
                    )
        return result

    def _create_datetime(self, date: str, time: str) -> datetime:
        """
        Creates the datetime from the extracted date and time as strings
        :param date the date in format mm/dd/yyyy
        :param time the time in format HHMM

        :return Returns the datetime from the given date and time strings.
        :rtype datetime
        """
        d = datetime.strptime(date, self.date_format)
        if time == "2400":
            d = d + timedelta(days=1)
        else:
            t = datetime.strptime(time, self.time_format)
            d = datetime.combine(d.date(), t.time())
        return d

    def _get_table(self) -> Tag:
        """Gets the datatable as a BeautifulSoup Tag instance."""
        response = requests.get(self.url)
        soup = BeautifulSoup(response.content, "html.parser")
        return soup.find("table", class_="tableStyle")

    @staticmethod
    def _extract_headers(tag: Tag) -> List[str]:
        """Extracts the text for each header cell using the table provided tag."""
        rows = tag.find_all("tr")
        headers = rows[0].find_all("th")
        result = []
        for header in headers:
            result.append(header.text)
        return result
