from bs4 import BeautifulSoup

from aimbot.scrapers.weather import WeatherScraper

# Mirrors the BBC tide-table markup: the tide type lives in the first <td> of
# each data row, the header row uses <th>, and a "Current tide" row is present.
TIDE_TABLE_HTML = """
<table class="ssrcss-1pwsb40-TableWrapper e1icz102">
  <thead>
    <tr>
      <th scope="col">Type of tide</th>
      <th scope="col">Time (BST)</th>
      <th scope="col">Height (metres)</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>High</td><td>01:49 1 hour 49 minutes</td><td>7.8 7.8 metres</td></tr>
    <tr><td>Low</td><td>08:26 8 hours 26 minutes</td><td>4.4 4.4 metres</td></tr>
    <tr><td>High</td><td>14:31 14 hours 31 minutes</td><td>8.1 8.1 metres</td></tr>
    <tr><td>Current tide</td><td>19:55 19 hours 55 minutes</td><td>4.4 4.4 metres</td></tr>
    <tr><td>Low</td><td>21:28 21 hours 28 minutes</td><td>3.9 3.9 metres</td></tr>
  </tbody>
</table>
"""


def test_parse_tides_from_current_bbc_markup():
    soup = BeautifulSoup(TIDE_TABLE_HTML, "html.parser")
    assert WeatherScraper.parse_tides(soup) == (
        "Low tides at 08:26 AM, 09:28 PM, with high tides at 01:49 AM, 02:31 PM"
    )


def test_parse_tides_ignores_current_tide_row():
    soup = BeautifulSoup(TIDE_TABLE_HTML, "html.parser")
    tides = WeatherScraper.parse_tides(soup)
    assert "07:55 PM" not in tides
    assert "Current" not in tides


def test_parse_tides_without_table_is_empty():
    soup = BeautifulSoup("<html><body><p>No tides here</p></body></html>", "html.parser")
    assert WeatherScraper.parse_tides(soup) == "Low tides at , with high tides at"


def test_parse_tides_header_only_does_not_crash():
    soup = BeautifulSoup(
        "<table><thead><tr><th>Type of tide</th><th>Time</th></tr></thead></table>",
        "html.parser",
    )
    assert WeatherScraper.parse_tides(soup) == "Low tides at , with high tides at"
