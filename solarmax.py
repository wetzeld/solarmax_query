import socket

class SolarMax():
    def __init__(self, host: str, port: int, inverterIndex: int) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #type: socket.socket
        self.index = inverterIndex
        self.connect(host, port)
    
    def __del__(self) -> None:
        if self.socket is not None:
            self.socket.close()
    
    def connect(self, host:str , port: int) -> None:
        try:
            self.socket.connect((host, port))
        except:
            self.socket.close()
            self.socket = None
            raise Exception("Could not connect to host: {}".format(host))
    
    def hexValue(self, i: int) -> str:
        return (hex(i)[2:]).upper()
    
    def checksum(self, text: str) -> str:
        total = 0
        for c in text:
            total += ord(c)
        crc = self.hexValue(total)
        while len(crc) < 4:
            crc = '0'+crc
        return crc
    
    def createQueryString(self, code: str) -> str:
        # For the structure see 1.1

        # FB is hex for 251 wich is the reserved aress for an outsite host wich we are see 1.3
        srcAddress = "FB"

        # inverterIndex is the index of the inverter we want to query wich is converted to hex wich has to be 2 characters long see 1.1
        destAddress = self.hexValue(self.index)
        if len(destAddress) < 2:
            destAddress = '0'+destAddress

        # this the "port" in hex wich for data query is always 100 see 1.4
        queryType = "64"

        lenght = 1 + 3 + 3 + 3 + 3 + len(code) + 1 + 4 + 1
        lenght = self.hexValue(lenght)
        preCrcString = f"{srcAddress};{destAddress};{lenght}|{queryType}:{code}|"

        # this is the checksum of the query see 1.1
        crc = self.checksum(preCrcString)
        queryString = "{" + preCrcString + crc + "}"

        return queryString

    def parseData(self, data: str) -> int:
        # data is the data from the inverter
        # for example "{01;FB;18|64:ADR=1|04A9}"
        # we are only interested in the data part
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
        queryString = self.createQueryString(code)

        # send query
        self.socket.send(queryString.encode())
        #recive query
        data = ""
        while len(data) < 1:
            data = self.socket.recv(255).decode()
        
        # check crc
        inCrc = data[-5:-1]
        checkCrc = self.checksum(data[1:-5])
        if inCrc != checkCrc:
            raise Exception("CRC check failed")
        
        # parse data
        return self.parseData(data)

    def getUnit(self, funktion: object) -> str:
        units = {
            self.acOutput: "W",
            self.operatingHours: "h",
            self.dateYear: "a",
            self.dateMonth: "m",
            self.dateDay: "d",
            self.energyYear: "kWh",
            self.energyMonth: "kWh",
            self.energyDay: "kWh",
            self.energyTotal: "kWh",
            self.installedCapacity: "W",
            self.mainsCycleDuration: "μs",
            self.networkAddress: "",
            self.relativeOutput: "%",
            self.softwareVersion: "",
            self.voltageDC: "V",
            self.voltagePhaseOne: "V",
            self.currentDC: "A",
            self.temperaturePowerUnitOne: "°C",
            self.model: "",
            self.timeMinutes: "min",
            self.timeHours: "h",
        }
        return units[funktion]

    def model(self) -> str:
        inverter_types = {
            20010: { 'desc': 'SolarMax 2000S', 'max': 2000, },
            20020: { 'desc': 'SolarMax 3000S', 'max': 3000, },
            20030: { 'desc': 'SolarMax 4200S', 'max': 4200, },
            20040: { 'desc': 'SolarMax 6000S', 'max': 6000, },
        }
        return inverter_types[self.type()]['desc']

    def status(self) -> str:
        status_codes = {
            20000: 'Keine Kommunikation',
            20001: 'In Betrieb',
            20002: 'Zu wenig Einstrahlung',
            20003: 'Anfahren',
            20004: 'Betrieb auf MPP',
            20005: 'Ventilator läuft',
            20006: 'Betrieb auf Maximalleistung',
            20007: 'Temperaturbegrenzung',
            20008: 'Netzbetrieb',
        }
        return status_codes[self.query("SYS")]
    
    def alarmCode(self) -> str:
        alarm_codes = {
            0: 'kein Fehler',
            1: 'Externer Fehler 1',
            2: 'Isolationsfehler DC-Seite',
            4: 'Fehlerstrom Erde zu Groß',
            8: 'Sicherungsbruch Mittelpunkterde',
            16: 'Externer Alarm 2',
            32: 'Langzeit-Temperaturbegrenzung',
            64: 'Fehler AC-Einspeisung',
            128: 'Externer Alarm 4',
            256: 'Ventilator defekt',
            512: 'Sicherungsbruch',
            1024: 'Ausfall Temperatursensor',
            2048: 'Alarm 12',
            4096: 'Alarm 13',
            8192: 'Alarm 14',
            16384: 'Alarm 15',
            32768: 'Alarm 16',
            65536: 'Alarm 17',
        }
        return alarm_codes[self.query("SAL")]

    def acOutput(self) -> float:
        data = self.query("PAC")
        return round(data * 0.5, 1)
    
    def operatingHours(self) -> int:
        return self.query("KHR")

    def dateYear(self) -> int:
        return self.query("DYR")
    
    def dateMonth(self) -> int:
        return self.query("DMT")
    
    def dateDay(self) -> int:
        return self.query("DDY")
    
    def energyYear(self) -> int:
        return self.query("KYR")
    
    def energyMonth(self) -> int:
        return self.query("KMT")
    
    def energyDay(self) -> float:
        return round(self.query("KDY") * 0.1, 1)
    
    def energyTotal(self) -> int:
        return self.query("KT0")
    
    def installedCapacity(self) -> float:
        return round(self.query("PIN") * 0.5, 1)
    
    def mainsCycleDuration(self) -> int:
        return self.query("TNP")
    
    def networkAddress(self) -> int:
        return self.query("ADR")
    
    def relativeOutput(self) -> int:
        return self.query("PRL")
    
    def softwareVersion(self) -> int:
        return self.query("SWV")
    
    def voltageDC(self) -> float:
        return round(self.query("UDC") * 0.1, 1)
    
    def voltagePhaseOne(self) -> float:
        return round(self.query("UL1") * 0.1, 1)
    
    def currentDC(self) -> float:
        return round(self.query("IDC") * 0.01, 2)
    
    def currentPhaseOne(self) -> float:
        return round(self.query("IL1") * 0.01, 2)
    
    def temperaturePowerUnitOne(self) -> int:
        return self.query("TKK")
    
    def type(self) -> int:
        return self.query("TYP")
    
    def timeMinutes(self) -> int:
        return self.query("TMI")
    
    def timeHours(self) -> int:
        return self.query("THR")
        