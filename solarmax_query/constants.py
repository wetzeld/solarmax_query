from enum import StrEnum


class SolarMaxQueryKey(StrEnum):
    STATUS = "SYS"
    ALARM_CODE = "SAL"
    AC_OUTPUT = "PAC"
    OPERATING_HOURS = "KHR"
    DATE_YEAR = "DYR"
    DATE_MONTH = "DMT"
    DATE_DAY = "DDY"
    ENERGY_YEAR = "KYR"
    ENERGY_MONTH = "KMT"
    ENERGY_DAY = "KDY"
    ENERGY_TOTAL = "KT0"
    INSTALLED_CAPACITY = "PIN"
    MAINS_CYCLE_DURATION = "TNP"
    NETWORK_ADDRESS = "ADR"
    RELATIVE_OUTPUT = "PRL"
    SOFTWARE_VERSION = "SWV"
    VOLTAGE_DC = "UDC"
    VOLTAGE_PHASE_ONE = "UL1"
    CURRENT_DC = "IDC"
    CURRENT_PHASE_ONE = "IL1"
    TEMPERATURE_POWER_UNIT_ONE = "TKK"
    TYPE = "TYP"
    TIME_HOURS = "THR"
    TIME_MINUTES = "TMI"
    MAINS_FREQUENCY = "TNF"


INVERTER_TYPES = {
    20010: "SolarMax 2000S",
    20020: "SolarMax 3000S",
    20030: "SolarMax 4200S",
    20040: "SolarMax 6000S",
}

STATUS_CODES = {
    20000: "Keine Kommunikation",
    20001: "In Betrieb",
    20002: "Zu wenig Einstrahlung",
    20003: "Anfahren",
    20004: "Betrieb auf MPP",
    20005: "Ventilator läuft",
    20006: "Betrieb auf Maximalleistung",
    20007: "Temperaturbegrenzung",
    20008: "Netzbetrieb",
}

ALARM_CODES = {
    0: "kein Fehler",
    1: "Externer Fehler 1",
    2: "Isolationsfehler DC-Seite",
    4: "Fehlerstrom Erde zu Groß",
    8: "Sicherungsbruch Mittelpunkterde",
    16: "Externer Alarm 2",
    32: "Langzeit-Temperaturbegrenzung",
    64: "Fehler AC-Einspeisung",
    128: "Externer Alarm 4",
    256: "Ventilator defekt",
    512: "Sicherungsbruch",
    1024: "Ausfall Temperatursensor",
    2048: "Alarm 12",
    4096: "Alarm 13",
    8192: "Alarm 14",
    16384: "Alarm 15",
    32768: "Alarm 16",
    65536: "Alarm 17",
}
