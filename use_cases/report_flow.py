"""Report context preparation for application layer orchestration."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Tuple

import pandas as pd


class ReportRoute(str, Enum):
    MENU = "menu"
    INFLATION = "inflation"
    ABC = "abc"
    SIMULATOR = "simulator"
    WEEKDAYS = "weekdays"
    PROCUREMENT = "procurement"


REPORT_TAB_LABELS: Tuple[str, ...] = (
    "![Rev](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93ZmZjYzAwIiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93ZmZjYzAwKSIgc3Ryb2tlPSIjZmZjYzAwIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPGNpcmNsZSBjeD0iOCIgY3k9IjgiIHI9IjYiLz48cGF0aCBkPSJNMTguMDkgMTAuMzdBNiA2IDAgMSAxIDEwLjM0IDE4Ii8+PHBhdGggZD0iTTcgNmgxdjQiLz48cGF0aCBkPSJtMTYuNzEgMTMuODguNy43MS0yLjgyIDIuODIiLz4gICAgPC9nPiAgICA8IS0tIFNoYXJwIHdoaXRlIGNvcmUgZm9yIHRoZSBuZW9uIHR1YmUgZWZmZWN0IC0tPiAgICA8ZyBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMSIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj4gICAgICA8Y2lyY2xlIGN4PSI4IiBjeT0iOCIgcj0iNiIvPjxwYXRoIGQ9Ik0xOC4wOSAxMC4zN0E2IDYgMCAxIDEgMTAuMzQgMTgiLz48cGF0aCBkPSJNNyA2aDF2NCIvPjxwYXRoIGQ9Im0xNi43MSAxMy44OC43LjcxLTIuODIgMi44MiIvPiAgICA8L2c+ICA8L2c+PC9zdmc+) Выручка",
    "![Inf](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93ZmYzMzMzIiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93ZmYzMzMzKSIgc3Ryb2tlPSIjZmYzMzMzIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPHBvbHlsaW5lIHBvaW50cz0iMjIgNyAxMy41IDE1LjUgOC41IDEwLjUgMiAxNyIvPjxwb2x5bGluZSBwb2ludHM9IjE2IDcgMjIgNyAyMiAxMyIvPiAgICA8L2c+ICAgIDwhLS0gU2hhcnAgd2hpdGUgY29yZSBmb3IgdGhlIG5lb24gdHViZSBlZmZlY3QgLS0+ICAgIDxnIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSIxIiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPiAgICAgIDxwb2x5bGluZSBwb2ludHM9IjIyIDcgMTMuNSAxNS41IDguNSAxMC41IDIgMTciLz48cG9seWxpbmUgcG9pbnRzPSIxNiA3IDIyIDcgMjIgMTMiLz4gICAgPC9nPiAgPC9nPjwvc3ZnPg==) Инфляция С/С",
    "![ABC](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93MDBmZjg4IiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93MDBmZjg4KSIgc3Ryb2tlPSIjMDBmZjg4IiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPGxpbmUgeDE9IjE4IiB5MT0iMjAiIHgyPSIxOCIgeTI9IjEwIi8+PGxpbmUgeDE9IjEyIiB5MT0iMjAiIHgyPSIxMiIgeTI9IjQiLz48bGluZSB4MT0iNiIgeTE9IjIwIiB4Mj0iNiIgeTI9IjE0Ii8+ICAgIDwvZz4gICAgPCEtLSBTaGFycCB3aGl0ZSBjb3JlIGZvciB0aGUgbmVvbiB0dWJlIGVmZmVjdCAtLT4gICAgPGcgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjEiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPGxpbmUgeDE9IjE4IiB5MT0iMjAiIHgyPSIxOCIgeTI9IjEwIi8+PGxpbmUgeDE9IjEyIiB5MT0iMjAiIHgyPSIxMiIgeTI9IjQiLz48bGluZSB4MT0iNiIgeTE9IjIwIiB4Mj0iNiIgeTI9IjE0Ii8+ICAgIDwvZz4gIDwvZz48L3N2Zz4=) ABC-анализ",
    "![Sim](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93ZmY5OTAwIiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93ZmY5OTAwKSIgc3Ryb2tlPSIjZmY5OTAwIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPGxpbmUgeDE9IjQiIHkxPSIyMSIgeDI9IjQiIHkyPSIxNCIvPjxsaW5lIHgxPSI0IiB5MT0iMTAiIHgyPSI0IiB5Mj0iMyIvPjxsaW5lIHgxPSIxMiIgeTE9IjIxIiB4Mj0iMTIiIHkyPSIxMiIvPjxsaW5lIHgxPSIxMiIgeTE9IjgiIHgyPSIxMiIgeTI9IjMiLz48bGluZSB4MT0iMjAiIHkxPSIyMSIgeDI9IjIwIiB5Mj0iMTYiLz48bGluZSB4MT0iMjAiIHkxPSIxMiIgeDI9IjIwIiB5Mj0iMyIvPjxsaW5lIHgxPSIxIiB5MT0iMTQiIHgyPSI3IiB5Mj0iMTQiLz48bGluZSB4MT0iOSIgeTE9IjgiIHgyPSIxNSIgeTI9IjgiLz48bGluZSB4MT0iMTciIHkxPSIxNiIgeDI9IjIzIiB5Mj0iMTYiLz4gICAgPC9nPiAgICA8IS0tIFNoYXJwIHdoaXRlIGNvcmUgZm9yIHRoZSBuZW9uIHR1YmUgZWZmZWN0IC0tPiAgICA8ZyBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMSIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj4gICAgICA8bGluZSB4MT0iNCIgeTE9IjIxIiB4Mj0iNCIgeTI9IjE0Ii8+PGxpbmUgeDE9IjQiIHkxPSIxMCIgeDI9IjQiIHkyPSIzIi8+PGxpbmUgeDE9IjEyIiB5MT0iMjEiIHgyPSIxMiIgeTI9IjEyIi8+PGxpbmUgeDE9IjEyIiB5MT0iOCIgeDI9IjEyIiB5Mj0iMyIvPjxsaW5lIHgxPSIyMCIgeTE9IjIxIiB4Mj0iMjAiIHkyPSIxNiIvPjxsaW5lIHgxPSIyMCIgeTE9IjEyIiB4Mj0iMjAiIHkyPSIzIi8+PGxpbmUgeDE9IjEiIHkxPSIxNCIgeDI9IjciIHkyPSIxNCIvPjxsaW5lIHgxPSI5IiB5MT0iOCIgeDI9IjE1IiB5Mj0iOCIvPjxsaW5lIHgxPSIxNyIgeTE9IjE2IiB4Mj0iMjMiIHkyPSIxNiIvPiAgICA8L2c+ICA8L2c+PC9zdmc+) Симулятор",
    "![Days](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93Y2M2NmZmIiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93Y2M2NmZmKSIgc3Ryb2tlPSIjY2M2NmZmIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPHJlY3QgeD0iMyIgeT0iNCIgd2lkdGg9IjE4IiBoZWlnaHQ9IjE4IiByeD0iMiIgcnk9IjIiLz48bGluZSB4MT0iMTYiIHkxPSIyIiB4Mj0iMTYiIHkyPSI2Ii8+PGxpbmUgeDE9IjgiIHkxPSIyIiB4Mj0iOCIgeTI9IjYiLz48bGluZSB4MT0iMyIgeTE9IjEwIiB4Mj0iMjEiIHkyPSIxMCIvPiAgICA8L2c+ICAgIDwhLS0gU2hhcnAgd2hpdGUgY29yZSBmb3IgdGhlIG5lb24gdHViZSBlZmZlY3QgLS0+ICAgIDxnIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSIxIiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPiAgICAgIDxyZWN0IHg9IjMiIHk9IjQiIHdpZHRoPSIxOCIgaGVpZ2h0PSIxOCIgcng9IjIiIHJ5PSIyIi8+PGxpbmUgeDE9IjE2IiB5MT0iMiIgeDI9IjE2IiB5Mj0iNiIvPjxsaW5lIHgxPSI4IiB5MT0iMiIgeDI9IjgiIHkyPSI2Ii8+PGxpbmUgeDE9IjMiIHkxPSIxMCIgeDI9IjIxIiB5Mj0iMTAiLz4gICAgPC9nPiAgPC9nPjwvc3ZnPg==) Дни недели",
    "![Proc](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCIgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0Ij4gIDxkZWZzPiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImdsQmFzZSIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+ICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iIzJhMmEyYSIgc3RvcC1vcGFjaXR5PSIwLjgiLz4gICAgICA8c3RvcCBvZmZzZXQ9IjEwMCUiIHN0b3AtY29sb3I9IiMwNTA1MDUiIHN0b3Atb3BhY2l0eT0iMC45Ii8+ICAgIDwvbGluZWFyR3JhZGllbnQ+ICAgIDxsaW5lYXJHcmFkaWVudCBpZD0iZ2xIaWdobGlnaHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMCUiIHkyPSIxMDAlIj4gICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMyIvPiAgICAgIDxzdG9wIG9mZnNldD0iNTAlIiBzdG9wLWNvbG9yPSIjZmZmZmZmIiBzdG9wLW9wYWNpdHk9IjAuMCIvPiAgICA8L2xpbmVhckdyYWRpZW50PiAgICA8ZmlsdGVyIGlkPSJnbG93MDBjY2ZmIiB4PSItMjAlIiB5PSItMjAlIiB3aWR0aD0iMTQwJSIgaGVpZ2h0PSIxNDAlIj4gICAgICA8ZmVHYXVzc2lhbkJsdXIgc3RkRGV2aWF0aW9uPSIzIiByZXN1bHQ9ImJsdXIiIC8+ICAgICAgPGZlQ29tcG9zaXRlIGluPSJTb3VyY2VHcmFwaGljIiBpbjI9ImJsdXIiIG9wZXJhdG9yPSJvdmVyIiAvPiAgICA8L2ZpbHRlcj4gIDwvZGVmcz4gICAgPCEtLSBPdXRlciBnbGFzcyBib3VuZGFyeSAmIGRyb3Agc2hhZG93IC0tPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xCYXNlKSIvPiAgPHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjU2IiBoZWlnaHQ9IjU2IiByeD0iMTQiIGZpbGw9InVybCgjZ2xIaWdobGlnaHQpIi8+ICAgIDwhLS0gR2xhc3MgaW5uZXIgcmltICh0b3AgcmltIGhpZ2hsaWdodCB0byBtYWtlIGl0IDNEKSAtLT4gIDxwYXRoIGQ9Ik0gMTYsNCBMIDQ4LDQgQyA1NSw0IDYwLDkgNjAsMTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuNCIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgPCEtLSBHbGFzcyBib3R0b20gcmltIHJlZmxlY3Rpb24gLS0+ICA8cGF0aCBkPSJNIDQsNDggQyA0LDU1IDksNjAgMTYsNjAgTCA0OCw2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utb3BhY2l0eT0iMC4xIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPiAgICA8IS0tIElubmVyIEljb24gQ2VudGVyZWQgLS0+ICA8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxNiwgMTYpIHNjYWxlKDEuMzMzKSI+ICAgIDxnIGZpbHRlcj0idXJsKCNnbG93MDBjY2ZmKSIgc3Ryb2tlPSIjMDBjY2ZmIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+ICAgICAgPHBhdGggZD0ibTcuNSA0LjI3IDkgNS4xNSIvPjxwYXRoIGQ9Ik0yMSA4YTIgMiAwIDAgMC0xLTEuNzNsLTctNGEyIDIgMCAwIDAtMiAwbC03IDRBMiAyIDAgMCAwIDMgOHY4YTIgMiAwIDAgMCAxIDEuNzNsNyA0YTIgMiAwIDAgMCAyIDBsNy00QTIgMiAwIDAgMCAyMSAxNloiLz48cGF0aCBkPSJtMy4zIDcgOC43IDUgOC43LTUiLz48cGF0aCBkPSJNMTIgMjJWMTIiLz4gICAgPC9nPiAgICA8IS0tIFNoYXJwIHdoaXRlIGNvcmUgZm9yIHRoZSBuZW9uIHR1YmUgZWZmZWN0IC0tPiAgICA8ZyBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMSIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj4gICAgICA8cGF0aCBkPSJtNy41IDQuMjcgOSA1LjE1Ii8+PHBhdGggZD0iTTIxIDhhMiAyIDAgMCAwLTEtMS43M2wtNy00YTIgMiAwIDAgMC0yIDBsLTcgNEEyIDIgMCAwIDAgMyA4djhhMiAyIDAgMCAwIDEgMS43M2w3IDRhMiAyIDAgMCAwIDIgMGw3LTRBMiAyIDAgMCAwIDIxIDE2WiIvPjxwYXRoIGQ9Im0zLjMgNyA4LjcgNSA4LjctNSIvPjxwYXRoIGQ9Ik0xMiAyMlYxMiIvPiAgICA8L2c+ICA8L2c+PC9zdmc+) Закупки",
) Выручка",
    "![Inf](https://cdn-icons-png.flaticon.com/128/9355/9355642.png) Инфляция С/С",
    "![ABC](https://cdn-icons-png.flaticon.com/128/10427/10427181.png) ABC-анализ",
    "![Sim](https://cdn-icons-png.flaticon.com/128/10397/10397034.png) Симулятор",
    "![Days](https://cdn-icons-png.flaticon.com/128/10691/10691802.png) Дни недели",
    "![Proc](https://cdn-icons-png.flaticon.com/128/10427/10427216.png) Закупки",
)

_ROUTE_BY_LABEL = {
    REPORT_TAB_LABELS[0]: ReportRoute.MENU,
    REPORT_TAB_LABELS[1]: ReportRoute.INFLATION,
    REPORT_TAB_LABELS[2]: ReportRoute.ABC,
    REPORT_TAB_LABELS[3]: ReportRoute.SIMULATOR,
    REPORT_TAB_LABELS[4]: ReportRoute.WEEKDAYS,
    REPORT_TAB_LABELS[5]: ReportRoute.PROCUREMENT,
}


def select_report_route(selected_tab_label: str) -> ReportRoute:
    """Map selected report tab label to route id with safe fallback."""
    return _ROUTE_BY_LABEL.get(selected_tab_label, ReportRoute.MENU)


@dataclass(frozen=True)
class ReportContext:
    """Prepared data context for report rendering."""

    df_current: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_prev: pd.DataFrame = field(default_factory=pd.DataFrame)
    current_label: str = ""
    prev_label: str = ""
    selected_period: Optional["SelectedPeriod"] = None


@dataclass(frozen=True)
class SelectedPeriod:
    start: datetime
    end: datetime
    days: int
    inflation_start: datetime


def build_report_context(
    df_full: Optional[pd.DataFrame],
    period_mode: str,
    *,
    selected_ym: Any = None,
    scope_mode: str = "Весь месяц",
    selected_day: Optional[int] = None,
    compare_mode: str = "Год назад",
    date_range: Optional[Tuple[Any, Any]] = None,
    now: Optional[datetime] = None,
) -> ReportContext:
    """Build report DataFrame slices and labels from selected period parameters."""
    if df_full is None or df_full.empty:
        return ReportContext()

    if period_mode == "📌 Последний загруженный день":
        last_day = pd.to_datetime(df_full["Дата_Отчета"]).max().normalize()
        day_start = last_day
        day_end = last_day + timedelta(hours=23, minutes=59, seconds=59)
        df_current = df_full[(df_full["Дата_Отчета"] >= day_start) & (df_full["Дата_Отчета"] <= day_end)]
        return ReportContext(
            df_current=df_current,
            df_prev=pd.DataFrame(),
            current_label=f"{last_day.strftime('%d.%m.%Y')} (последний загруженный день)",
            prev_label="",
            selected_period=SelectedPeriod(
                start=day_start,
                end=day_end,
                days=1,
                inflation_start=day_start.replace(day=1),
            ),
        )

    if period_mode == "📅 Месяц (Сравнение)":
        if selected_ym is None:
            return ReportContext()

        start_cur = selected_ym.start_time
        end_cur = selected_ym.end_time
        if scope_mode == "По конкретный день":
            if selected_day is None:
                reference_dt = now or datetime.now()
                max_d = int(selected_ym.to_timestamp(how="end").day)
                selected_day = min(reference_dt.day, max_d)
            end_cur = start_cur + timedelta(days=selected_day - 1)
            end_cur = end_cur.replace(hour=23, minute=59, second=59)

        df_current = df_full[(df_full["Дата_Отчета"] >= start_cur) & (df_full["Дата_Отчета"] <= end_cur)]
        df_prev = pd.DataFrame()
        prev_label = ""

        if compare_mode == "Предыдущий месяц":
            prev_ym = selected_ym - 1
            start_prev = prev_ym.start_time
            end_prev = start_prev + (end_cur - start_cur)
            df_prev = df_full[(df_full["Дата_Отчета"] >= start_prev) & (df_full["Дата_Отчета"] <= end_prev)]
            prev_label = prev_ym.strftime("%b %Y")
        elif compare_mode == "Год назад":
            prev_ym = selected_ym - 12
            start_prev = prev_ym.start_time
            end_prev = start_prev + (end_cur - start_cur)
            df_prev = df_full[(df_full["Дата_Отчета"] >= start_prev) & (df_full["Дата_Отчета"] <= end_prev)]
            prev_label = prev_ym.strftime("%b %Y")

        return ReportContext(
            df_current=df_current,
            df_prev=df_prev,
            current_label=f"{selected_ym.strftime('%b %Y')} ({scope_mode})",
            prev_label=prev_label,
            selected_period=SelectedPeriod(
                start=start_cur,
                end=end_cur,
                days=(end_cur - start_cur).days + 1,
                inflation_start=start_cur,
            ),
        )

    if period_mode == "📆 Диапазон" and isinstance(date_range, tuple) and len(date_range) == 2:
        start_raw, end_raw = date_range
        start_dt = pd.to_datetime(start_raw)
        end_dt = pd.to_datetime(end_raw) + timedelta(hours=23, minutes=59)
        df_current = df_full[(df_full["Дата_Отчета"] >= start_dt) & (df_full["Дата_Отчета"] <= end_dt)]
        return ReportContext(
            df_current=df_current,
            df_prev=pd.DataFrame(),
            current_label=f"{start_dt.date()} - {end_dt.date()}",
            prev_label="",
            selected_period=SelectedPeriod(
                start=start_dt,
                end=end_dt,
                days=(end_dt - start_dt).days + 1,
                inflation_start=start_dt,
            ),
        )

    return ReportContext()
