import importlib
import time

I2C_CHUNK_SIZE = 28
I2C_REGISTER = 0x00

def _load_i2c_backend():
    for module_name in ("smbus2", "smbus"):
        try:
            module = importlib.import_module(module_name)
            return getattr(module, "SMBus", None), getattr(module, "i2c_msg", None), module_name
        except ImportError:
            continue

    return None, None, None


SMBus, i2c_msg, I2C_BACKEND = _load_i2c_backend()


class I2CController:
    def __init__(self, targets, name="ESP"):
        self.name = name
        self.targets = list(targets)
        self.connections = []
        self._buses = {}

        if SMBus is None:
            print(
                f"[{self.name}] I2C backend not available. Install smbus2 or smbus to enable eye I2C transport."
            )
            return

        for bus_number, address in self.targets:
            try:
                bus = self._buses.get(bus_number)
                if bus is None:
                    bus = SMBus(bus_number)
                    self._buses[bus_number] = bus
                    time.sleep(0.05)

                self.connections.append((bus_number, address, bus))
                print(
                    f"Connected to {self.name} on I2C bus {bus_number}, address 0x{address:02X} using {I2C_BACKEND}!"
                )
            except Exception as e:
                print(
                    f"Error connecting to {self.name} on I2C bus {bus_number}, address 0x{address:02X}: {e}"
                )

    def is_ready(self):
        return len(self.connections) > 0

    def _iter_chunks(self, payload):
        for offset in range(0, len(payload), I2C_CHUNK_SIZE):
            yield payload[offset : offset + I2C_CHUNK_SIZE]

    def _write_payload(self, bus, address, payload):
        for chunk in self._iter_chunks(payload):
            if i2c_msg is not None:
                bus.i2c_rdwr(i2c_msg.write(address, chunk))
            else:
                bus.write_i2c_block_data(address, I2C_REGISTER, list(chunk))
            time.sleep(0.002)

    def send_raw_line(self, line: str):
        if not self.is_ready():
            return

        msg = str(line)
        if not msg.endswith("\n"):
            msg += "\n"

        payload = msg.encode("utf-8")

        for bus_number, address, bus in self.connections:
            try:
                self._write_payload(bus, address, payload)
            except Exception as e:
                print(
                    f"[{self.name}] send error on I2C bus {bus_number}, address 0x{address:02X}: {e}"
                )

    def send_command(self, cmd: str):
        cmd = cmd.strip().upper()
        self.send_raw_line(cmd)

    def close(self):
        for bus in self._buses.values():
            try:
                bus.close()
            except Exception:
                pass

        self._buses = {}
        self.connections = []