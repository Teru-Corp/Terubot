# serial_com.py
import serial
import time

BAUD_RATE = 115200

class SerialController:
    def __init__(self, ports, name="ESP"):
        self.name = name
        self.ports = ports
        self.connections = []

        for port in ports:
            try:
                print(f"Connecting to {self.name} on {port}...")
                ser = serial.Serial(port, BAUD_RATE, timeout=0.2)
                time.sleep(1.2)
                ser.reset_input_buffer()
                self.connections.append(ser)
                print(f"Connected to {port}!")
            except Exception as e:
                print(f"Error connecting to {port}: {e}")

    def is_ready(self):
        return len(self.connections) > 0

    def send_raw_line(self, line: str):
        if not self.is_ready():
            return

        msg = str(line)
        if not msg.endswith("\n"):
            msg += "\n"

        payload = msg.encode("utf-8")

        for ser in self.connections:
            try:
                ser.write(payload)
                ser.flush()
            except Exception as e:
                print(f"[{self.name}] send error on {ser.port}: {e}")

    def send_char(self, c: str):
        c = c.strip().upper()
        if len(c) != 1:
            print(f"[{self.name}] expected single char, got {c}")
            return
        self.send_raw_line(c)

    def close(self):
        for ser in self.connections:
            try:
                ser.close()
            except:
                pass
        self.connections = []
