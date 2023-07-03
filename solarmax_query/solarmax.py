import socket, subprocess, os, time


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

    def create_query_string(self, code: str) -> str:
        # For the structure see 1.1

        # FB is hex for 251 which is the reserved address for an outside host which we are see 1.3
        src_address = "FB"

        # inverter_index is the index of the inverter we want to query which is converted to hex wich has to be 2 characters long see 1.1
        dest_address = f"{self.index:02X}"

        # this the "port" in hex wich for data query is always 100 see 1.4
        query_type = "64"

        length = 1 + 3 + 3 + 3 + 3 + len(code) + 1 + 4 + 1
        length = f"{length:02X}"
        pre_crc_string = f"{src_address};{dest_address};{length}|{query_type}:{code}|"

        # this is the checksum of the query see 1.1
        crc = self.checksum(pre_crc_string)
        query_string = "{" + pre_crc_string + crc + "}"

        return query_string

    def parse_data(self, data: str) -> int:
        # data is the data from the inverter
        # for example "{01;FB;18|64:ADR=1|04A9}"
        # we are only interested in the data part,
        # so we remove the header and the checksum
        # and convert the data to an int
        ndata = data.split("|")[1]
        if ndata == "":
            return None
        ndata = ndata.split("=")[1]
        if "," in ndata:
            ndata = ndata.split(",")[0]
        return int(ndata, 16)

    def query(self, code: str) -> int:
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
        inverter_types = {
            20010: "SolarMax 2000S",
            20020: "SolarMax 3000S",
            20030: "SolarMax 4200S",
            20040: "SolarMax 6000S",
        }
        data = self.type()
        if data is None:
            return None
        return inverter_types[data]

    def status(self) -> str:
        status_codes = {
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
        data = self.query("SYS")
        if data is None:
            return None
        return status_codes[data]

    def alarm_code(self) -> str:
        alarm_codes = {
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
        data = self.query("SAL")
        if data is None:
            return None
        return alarm_codes[data]

    def ac_output(self) -> float:
        data = self.query("PAC")
        if data is None:
            return None
        return round(data * 0.5, 1)

    def operating_hours(self) -> int:
        return self.query("KHR")

    def date_year(self) -> int:
        return self.query("DYR")

    def date_month(self) -> int:
        return self.query("DMT")

    def date_day(self) -> int:
        return self.query("DDY")

    def energy_year(self) -> int:
        return self.query("KYR")

    def energy_month(self) -> int:
        return self.query("KMT")

    def energy_day(self) -> float:
        data = self.query("KDY")
        if data is None:
            return None
        return round(data * 0.1, 1)

    def energy_total(self) -> int:
        return self.query("KT0")

    def installed_capacity(self) -> float:
        data = self.query("PIN")
        if data is None:
            return None
        return round(data * 0.5, 1)

    def mains_cycle_duration(self) -> int:
        return self.query("TNP")

    def network_address(self) -> int:
        return self.query("ADR")

    def relative_output(self) -> int:
        return self.query("PRL")

    def software_version(self) -> int:
        return self.query("SWV")

    def voltage_dc(self) -> float:
        data = self.query("UDC")
        if data is None:
            return None
        return round(data * 0.1, 1)

    def voltage_phase_one(self) -> float:
        data = self.query("UL1")
        if data is None:
            return None
        return round(data * 0.1, 1)

    def current_dc(self) -> float:
        data = self.query("IDC")
        if data is None:
            return None
        return round(data * 0.01, 2)

    def current_phase_one(self) -> float:
        data = self.query("IL1")
        if data is None:
            return None
        return round(data * 0.01, 2)

    def temperature_power_unit_one(self) -> int:
        return self.query("TKK")

    def type(self) -> int:
        return self.query("TYP")

    def time_minutes(self) -> int:
        return self.query("TMI")

    def time_hours(self) -> int:
        return self.query("THR")
