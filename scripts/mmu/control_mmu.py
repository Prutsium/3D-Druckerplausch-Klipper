#!/usr/bin/python3

import serial
import argparse

# device = "/dev/ttyS0"
# device = "COM4"
# device = "/dev/ttyAM0"
# device = "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0"
device = "/dev/ttyUSB0"

baudrate = 115200


class Mmucontrol():

	def __init__(self) -> None:
		print("MMU class init - Begin")
		self.connection = serial.Serial(port=device, baudrate=baudrate, timeout=1)
		if self.connection.isOpen():
			print("MMU connected.")
		else:
			print("MMU not connected.")
			exit(1)
		self.check_alive()

	def check_alive(self) -> None:
		self.connection.write(b'S1\n')
		version = str(self.connection.readline())
		print("Got version:", version)

		self.connection.write(b'S2\n')
		build = str(self.connection.readline())
		print("Got build number:", build)

	def check_ack(self) -> None:
		ack = str(self.connection.readline())
		if ack != "ok\n":
			print("WARN: Got other acknowledgement than ok\n :", ack)

	def filament_unload(self) -> None:
		print("Unloading Filament.")
		self.connection.write(b'U0\n')
		self.check_ack()

	def load_more_filament(self) -> None:
		print("Loading more Filament.")
		self.connection.write(b'C0\n')

	def load_filament_into_extruder(self, number: int) -> None:
		if number == 0:
			print("Loading Filament 0.")
			self.connection.write(b'T0\n')
		elif number == 1:
			print("Loading Filament 1.")
			self.connection.write(b'T1\n')
		elif number == 2:
			print("Loading Filament 2.")
			self.connection.write(b'T2\n')
		elif number == 3:
			print("Loading Filament 3.")
			self.connection.write(b'T3\n')
		elif number == 4:
			print("Loading Filament 4.")
			self.connection.write(b'T4\n')
		else:
			return
		self.check_ack()

	def load_filament_to_sensor(self, number: int) -> None:
		if number == 0:
			print("Loading Filament 0.")
			self.connection.write(b'L0\n')  # L0
		elif number == 1:
			print("Loading Filament 1.")
			self.connection.write(b'L1\n')  # L1
		elif number == 2:
			print("Loading Filament 2.")
			self.connection.write(b'L2\n')  # L2
		elif number == 3:
			print("Loading Filament 3.")
			self.connection.write(b'L3\n')  # L3
		elif number == 4:
			print("Loading Filament 4.")
			self.connection.write(b'L4\n')  # L4
		else:
			return
		self.check_ack()

	def eject_filament(self, number: int) -> None:
		if number == 0:
			print("Ejecting Filament 0.")
			self.connection.write(b'E0\n')
		elif number == 1:
			print("Ejecting Filament 1.")
			self.connection.write(b'E1\n')
		elif number == 2:
			print("Ejecting Filament 2.")
			self.connection.write(b'E2\n')
		elif number == 3:
			print("Ejecting Filament 3.")
			self.connection.write(b'E3\n')
		elif number == 4:
			print("Ejecting Filament 4.")
			self.connection.write(b'E4\n')
		else:
			return
		self.check_ack()

	def recover(self):
		print("Sending recover")
		self.connection.write(b'R0\n')

	def check_filament(self):
		print("Checking status")
		self.connection.write(b'P0\n')
		print(str(self.connection.readline()))


def argpaser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		prog=__file__,
		description="This Python 3 file is used to communicate with the MMU"
	)
	parser.add_argument(
		"-l", "--load",
		action="store_true",
		help="Load Filament (L0-L4). Add Parameter --slot/-s"
	)
	parser.add_argument(
		"-c", "--change",
		action="store_true",
		help="Load Filament (T0-T4). Add Parameter --slot/-s"
	)
	parser.add_argument(
		"-e", "--eject",
		action="store_true",
		help="Eject Filament (E0-E4). Add Parameter --slot/-s"
	)
	parser.add_argument(
		"-u", "--unload",
		action="store_true",
		help="Unload filament. (U0)"
	)
	parser.add_argument(
		"-r", "--recover",
		action="store_true",
		help="Recover filament. (R0)"
	)
	parser.add_argument(
		"-m", "--more",
		action="store_true",
		help="Load more filament. (C0)"
	)
	parser.add_argument(
		"-f", "--finda",
		action="store_true",
		help="Returns FINDA filament sensor status. (P0)"
	)
	parser.add_argument(
		"-s", "--slot",
		metavar="n", nargs=1,
		help="Specify Slot 0-4"
	)
	return parser


if __name__ == "__main__":
	parser = argpaser()
	args = parser.parse_args()
	if args.load:
		if args.slot is not None:
			m = Mmucontrol()
			m.load_filament_to_sensor(args.slot)
		else:
			parser.print_help()
	elif args.change:
		if args.slot is not None:
			m = Mmucontrol()
			m.load_filament_into_extruder(args.slot)
		else:
			parser.print_help()
	elif args.eject:
		if args.slot is not None:
			m = Mmucontrol()
			m.load_filament_into_extruder(args.slot)
		else:
			parser.print_help()
	elif args.unload:
		m = Mmucontrol()
		m.filament_unload()
	elif args.recover:
		m = Mmucontrol()
		m.recover()
	elif args.finda:
		m = Mmucontrol()
		m.check_filament()
	else:
		parser.print_help()
