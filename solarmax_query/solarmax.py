import socket
import subprocess
import os
import time

from .constants import SolarMaxQueryKey, INVERTER_TYPES, STATUS_CODES, ALARM_CODES


class SolarMax:
    def __init__(self, host: str, port: int = 12345, inverter_index: int = 1) -> None:
        self.socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )  # type: socket.socket
        self.index = inverter_index
        self.host = host
        self.port = port
        self.connect()

    def __del__(self) -> None:
        if self.socket is not None:
            self.socket.close()

    def ping_inverter(self) -> bool:
        if os.name == "nt":
            out = subprocess.Popen(
                ["ping", "-n", "1", self.host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            out = subprocess.Popen(
                ["ping", "-c", "1", self.host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        out.wait()
        return out.returncode == 0

    def reconnect(self) -> None:
        self.__del__()
        while not self.ping_inverter():
            time.sleep(60)
        self.connect()

    def connect(self) -> None:
        if not self.ping_inverter():
            raise Exception("Inverter not reachable")
        try:
            self.socket.connect((self.host, self.port))
        except:
            self.socket.close()
            self.socket = None
            raise Exception(f"Could not connect to host: {self.host}:{self.port}")

    def checksum(self, text: str) -> str:
        total = 0
        for c in text:
            total += ord(c)
        crc = f"{total:04X}"
        while len(crc) < 4:
            crc = "0" + crc
        return crc

    def create_query_string(
        self, key: str | SolarMaxQueryKey | list[str] | list[SolarMaxQueryKey]
    ) -> str:
        # For the structure see 1.1

        if isinstance(key, list):
            key = ";".join(key)

        # FB is hex for 251 which is the reserved address for an outside host
        # which we are, see 1.3
        src_address = "FB"

        # inverter_index is the index of the inverter we want to query which is
        # converted to hex wich has to be 2 characters long see 1.1.
        dest_address = f"{self.index:02X}"

        # this the "port" in hex which for data query is always 100 see 1.4
        query_type = "64"

        length = 1 + 3 + 3 + 3 + 3 + len(key) + 1 + 4 + 1
        length = f"{length:02X}"
        pre_crc_string = f"{src_address};{dest_address};{length}|{query_type}:{key}|"

        # this is the checksum of the query see 1.1
        crc = self.checksum(pre_crc_string)
        query_string = "{" + pre_crc_string + crc + "}"

        return query_string

    def parse_data(self, data: str) -> dict | int | float | str:
        # data is the data from the inverter
        # for example "{01;FB;18|64:ADR=1|04A9}"
        # we are only interested in the data part,
        # so we remove the header and the checksum
        # and convert the data to an int
        ndata = data.split("|")[1]
        if ndata == "":
            return None
        port, ndata, *_ = ndata.split(":")
        if port != "64":
            return None
        elements = ndata.split(";")

        result = {}
        for element in elements:
            key, value = element.split("=")
            result[key] = self.parse_value(key, value)
        return result

    @staticmethod
    def parse_value(key: str | SolarMaxQueryKey, value: str) -> dict | int | float:
        if key == SolarMaxQueryKey.STATUS:
            return SolarMax.parse_status_code(value)

        if key == SolarMaxQueryKey.ALARM_CODE:
            return SolarMax.parse_alarm_code(value)

        if key == SolarMaxQueryKey.TYPE:
            return SolarMax.parse_type(value)

        if key in [SolarMaxQueryKey.CURRENT_DC, SolarMaxQueryKey.CURRENT_PHASE_ONE]:
            # Current Positive 2
            return round(int(value, 16) * 0.01, 2)

        if key in [SolarMaxQueryKey.AC_OUTPUT, SolarMaxQueryKey.INSTALLED_CAPACITY]:
            # Power
            return round(int(value, 16) * 0.5, 1)

        if key in [SolarMaxQueryKey.ENERGY_DAY]:
            # Energy 1
            return round(int(value, 16) * 0.1, 1)

        if key in [
            SolarMaxQueryKey.ENERGY_YEAR,
            SolarMaxQueryKey.ENERGY_MONTH,
            SolarMaxQueryKey.ENERGY_TOTAL,
        ]:
            # Energy 2
            return int(value, 16)

        if key in [SolarMaxQueryKey.VOLTAGE_DC, SolarMaxQueryKey.VOLTAGE_PHASE_ONE]:
            # Voltage 2
            return round(int(value, 16) * 0.1, 1)

        if key in [
            SolarMaxQueryKey.OPERATING_HOURS,
            SolarMaxQueryKey.SOFTWARE_VERSION,
            SolarMaxQueryKey.NETWORK_ADDRESS,
        ]:
            # Without Unit 1 and 2, Network Address
            return int(value, 16)

        if key in [
            SolarMaxQueryKey.DATE_DAY,
            SolarMaxQueryKey.DATE_MONTH,
            SolarMaxQueryKey.DATE_YEAR,
            SolarMaxQueryKey.TIME_HOURS,
            SolarMaxQueryKey.TIME_MINUTES,
            SolarMaxQueryKey.MAINS_CYCLE_DURATION,
        ]:
            # Various date / time fields
            return int(value, 16)

        if key in [
            SolarMaxQueryKey.RELATIVE_OUTPUT,
            SolarMaxQueryKey.TEMPERATURE_POWER_UNIT_ONE,
        ]:
            # Percent, Temperature_positive
            return int(value, 16)

        # unknown type, return the raw value.
        return value

    @staticmethod
    def parse_status_code(code: str) -> dict:
        # Example status code: "4E28,0"
        # It is unclear what the ',0' is used for, so for now we discard it
        code = code.split(",")[0]

        code = int(code, 16)
        status = STATUS_CODES.get(code, f"Unknown status '{code}'")
        return {"raw": code, "status": status}

    @staticmethod
    def parse_alarm_code(code: str) -> dict:
        code = int(code, 16)
        # TODO: in case alarm codes are a bitmask, we would need to handle
        #  multiple active alarms at once.
        alarm = ALARM_CODES.get(code, f"Unknown alarm code '{code}'")
        return {"raw": code, "alarm": alarm}

    @staticmethod
    def parse_type(code: str) -> dict:
        code = int(code, 16)
        model = INVERTER_TYPES.get(code, f"Unknown model '{code}'")
        return {"raw": code, "model": model}

    def query(
        self, code: str | SolarMaxQueryKey | list[str] | list[SolarMaxQueryKey]
    ) -> dict | int | float:
        query_string = self.create_query_string(code)

        try:
            # send query
            self.socket.sendall(query_string.encode())
            # receive reply
            data = ""
            while len(data) < 1:
                data = self.socket.recv(255).decode()
        except:
            return None

        # check crc
        in_crc = data[-5:-1]
        check_crc = self.checksum(data[1:-5])
        if in_crc != check_crc:
            return None

        # parse data
        return self.parse_data(data)

    def query_single(self, key: str | SolarMaxQueryKey) -> dict | int | float:
        return self.query(key).get(key)

    def get_unit(self, function: object) -> str:
        units = {
            self.ac_output: "W",
            self.operating_hours: "h",
            self.date_year: "a",
            self.date_month: "m",
            self.date_day: "d",
            self.energy_year: "kWh",
            self.energy_month: "kWh",
            self.energy_day: "kWh",
            self.energy_total: "kWh",
            self.installed_capacity: "W",
            self.mains_cycle_duration: "μs",
            self.network_address: "",
            self.relative_output: "%",
            self.software_version: "",
            self.voltage_dc: "V",
            self.voltage_phase_one: "V",
            self.current_dc: "A",
            self.temperature_power_unit_one: "°C",
            self.model: "",
            self.time_minutes: "min",
            self.time_hours: "h",
        }
        return units[function]

    def model(self) -> str:
        return self.query_single(SolarMaxQueryKey.TYPE).get("model")

    def status(self) -> str:
        return self.query_single(SolarMaxQueryKey.STATUS).get("status")

    def alarm_code(self) -> str:
        return self.query_single(SolarMaxQueryKey.ALARM_CODE).get("alarm")

    def ac_output(self) -> float:
        return self.query_single(SolarMaxQueryKey.AC_OUTPUT)

    def operating_hours(self) -> int:
        return self.query_single(SolarMaxQueryKey.OPERATING_HOURS)

    def date_year(self) -> int:
        return self.query_single(SolarMaxQueryKey.DATE_YEAR)

    def date_month(self) -> int:
        return self.query_single(SolarMaxQueryKey.DATE_MONTH)

    def date_day(self) -> int:
        return self.query_single(SolarMaxQueryKey.DATE_DAY)

    def energy_year(self) -> int:
        return self.query_single(SolarMaxQueryKey.ENERGY_YEAR)

    def energy_month(self) -> int:
        return self.query_single(SolarMaxQueryKey.ENERGY_MONTH)

    def energy_day(self) -> float:
        return self.query_single(SolarMaxQueryKey.ENERGY_DAY)

    def energy_total(self) -> int:
        return self.query_single(SolarMaxQueryKey.ENERGY_TOTAL)

    def installed_capacity(self) -> float:
        return self.query_single(SolarMaxQueryKey.INSTALLED_CAPACITY)

    def mains_cycle_duration(self) -> int:
        return self.query_single(SolarMaxQueryKey.MAINS_CYCLE_DURATION)

    def network_address(self) -> int:
        return self.query_single(SolarMaxQueryKey.NETWORK_ADDRESS)

    def relative_output(self) -> int:
        return self.query_single(SolarMaxQueryKey.RELATIVE_OUTPUT)

    def software_version(self) -> int:
        return self.query_single(SolarMaxQueryKey.SOFTWARE_VERSION)

    def voltage_dc(self) -> float:
        return self.query_single(SolarMaxQueryKey.VOLTAGE_DC)

    def voltage_phase_one(self) -> float:
        return self.query_single(SolarMaxQueryKey.VOLTAGE_PHASE_ONE)

    def current_dc(self) -> float:
        return self.query_single(SolarMaxQueryKey.CURRENT_DC)

    def current_phase_one(self) -> float:
        return self.query_single(SolarMaxQueryKey.CURRENT_PHASE_ONE)

    def temperature_power_unit_one(self) -> int:
        return self.query_single(SolarMaxQueryKey.TEMPERATURE_POWER_UNIT_ONE)

    def type(self) -> int:
        return self.query_single(SolarMaxQueryKey.TYPE).get("raw")

    def time_minutes(self) -> int:
        return self.query_single(SolarMaxQueryKey.TIME_MINUTES)

    def time_hours(self) -> int:
        return self.query_single(SolarMaxQueryKey.TIME_HOURS)
