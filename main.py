import serial
import serial.tools.list_ports

import click
import requests
import json
import time
import threading

import usb.core
import subprocess
import os

class SprigGroup(click.Group):
    def get_usage(self, ctx):
        return "Usage: sprig <command> [options]"

    def format_usage(self, ctx, formatter):
        formatter.write_text(self.get_usage(ctx))

@click.group(cls=SprigGroup)
def cli():
    "sprig CLI - a tool to help you interact with your Sprig"
    pass

def find_sprig_port():
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if port.vid is not None and port.pid is not None:
            if port.vid == 0x2e8a and port.pid == 0x000a:
                return port.device
            
    raise Exception("No Pi Pico found")

def spade_version(ser, verbose):
    "Get the version of your Sprig connected to this device"
    buffer = ""

    ser.write(b"VERSION")

    while True:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

            buffer += chunk

            if verbose:
                print("[SERIAL]", chunk)

            if "END" in buffer:
                break

    version = buffer.split(":")[1].split("END")[0]
    return version

def check_legacy(ser, verbose):
    ser.write(bytes([0, 1, 2, 3, 4]))

    buffer = ""

    while True:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            buffer += chunk

            if verbose:
                print("[SERIAL]", chunk)

            if '\n' in buffer:
                break

    if buffer.strip() == "found startup seq!":
        return True
    elif buffer.strip() == "legacy detected":
        return False
    
@cli.command()
@click.option('-v', '--verbose', is_flag=True)
def version(verbose):
    "Get the version of your Sprig connected to this device"
    try:
        ser = serial.Serial(find_sprig_port(), 115200, timeout=1)
    except serial.SerialException:
        print("It seems you don't have a Sprig connected to your computer. Please connect it and try again!")
        exit(1)

    ver = spade_version(ser, verbose)

    if ver:
        print(f"Your Sprig is on SPADE version: {ver}")

    ser.close()

@cli.command()
@click.argument('file', type=click.Path(exists=True),)
@click.option('-v', '--verbose', is_flag=True)
def upload(file, verbose):
    "Upload a game to your Sprig"

    try:
        ser = serial.Serial(find_sprig_port(), 115200, timeout=1)
    except serial.SerialException:
        print("It seems you don't have a Sprig connected to your computer. Please connect it and try again!")
        return

    if check_legacy(ser, verbose):
        print("Your Sprig is running on legacy firmware. Please update your firmware to use this command.")
        ser.close()
        exit(1)

    ver = spade_version(ser, verbose)

    res = requests.get('https://github.com/hackclub/sprig/raw/refs/heads/main/firmware/spade/src/version.json').text
    latest = json.loads(res).get('version')

    if ver != latest:
        print(f"Your Sprig is on SPADE version: {ver}")
        print(f"Please update your Sprig to the latest version: {latest}")
        ser.close()
        exit(1)

    if not file.endswith('.js'):
        print("Sprig can only recognise .js files. Please upload a .js file.")
        ser.close()
        exit(1)

    print(f"Uploading {file} to your Sprig...")

    if verbose:
        print("[UPLOAD > SERIAL] Writing startup sequence")
    ser.write(b"UPLOAD")

    filename = file[:-3] if file.endswith('.js') else file
    name_string = (filename + '\0' * (100 - len(filename)))[:100].encode('utf-8')

    if verbose:
        print("[UPLOAD > SERIAL] Writing file name")
    ser.write(name_string)

    with open(file, 'r') as f:
        contents = f.read()
    buf = contents.encode('utf-8')
    length = len(buf)

    if verbose:
        print("[UPLOAD > SERIAL] Writing file length")    
    ser.write(length.to_bytes(4, 'little'))

    start_time = time.time()
    timeout = 3
    serial_buffer = ""

    while time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            serial_buffer += chunk
            serial_buffer = serial_buffer[-128:]

            if verbose:
                print("[SERIAL]", chunk)

            if "OO_FLASH" in serial_buffer:
                value_split = serial_buffer.split("/")
                if "OO_FLASH" in value_split:
                    oo_index = value_split.index("OO_FLASH")
                    slots_needed = int(value_split[oo_index + 1])
                    slots_available = int(value_split[oo_index + 2])
                    print(f"Your Sprig does not have enough memory. Blocks needed: {slots_needed}, Blocks available: {slots_available}")
                ser.close()
                return
        break
    else:
        # Reached timeout
        print("Your Sprig does not have enough memory. Could not fetch block information.")
        ser.close()
        return
    
    if verbose:
        print("[UPLOAD > SERIAL] Writing file contents")

    thread = threading.Thread(target=ser.write, args=(buf,))
    thread.daemon = True
    thread.start()

    start_time = time.time()
    timeout = 30
    serial_buffer = ""

    while time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            serial_buffer += chunk
            serial_buffer = serial_buffer[-128:]

            if verbose:
                print("[SERIAL]", chunk)

            if "ALL_GOOD" in serial_buffer:
                print("Upload completed successfully!")
                break
            elif "OO_FLASH" in serial_buffer:
                value_split = serial_buffer.split("/")
                if "OO_FLASH" in value_split:
                    oo_index = value_split.index("OO_FLASH")
                    slots_needed = int(value_split[oo_index + 1])
                    slots_available = int(value_split[oo_index + 2])
                    print(f"Your Sprig does not have enough memory. Blocks needed: {slots_needed}, Blocks available: {slots_available}")
                ser.close()
                exit(1)
                return
        else:
            time.sleep(0.1)
    else:
        print("Upload timeout. Please try again. If this happens multiple times, your Sprig might not have enough memory to store this game.")    
        ser.close()
        exit(1)

    thread.join()

    ser.close()
    exit(0)

@cli.command()
@click.option('-v', '--verbose', is_flag=True)
def flash(verbose):
    "Flash your Sprig with the latest firmware"

    # Check if the Sprig is connected via usb
    sprigNormal = usb.core.find(idVendor=0x2e8a, idProduct=0x000a)
    sprig = usb.core.find(idVendor=0x2e8a, idProduct=0x0003)

    if sprig is None and sprigNormal is None:
        print("It seems you don't have a Sprig connected to your computer. Please connect it and try again!")
        return exit(1)
    
    if sprig is None and sprigNormal is not None:
        print("Your Sprig needs to be in BOOTSEL mode to flash the firmware. For more information: https://github.com/hackclub/sprig/blob/main/docs/UPLOAD.md#bootsel")
        return exit(1)

    firmware = requests.get('https://sprig.hackclub.com/pico-os.uf2').content

    # find where sprig is mounted
    def find_mount_point():
        platform = os.uname().sysname

        if platform == 'Linux':
            result = subprocess.run(['lsblk', '-o', 'NAME,MOUNTPOINT'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) == 2 and 'RPI-RP2' in parts[1]:
                    return parts[1]
        elif platform == 'Windows':
            result = subprocess.run(['wmic', 'logicaldisk', 'get', 'name, volumename'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) == 2 and 'RPI-RP2' in parts[1]:
                    return parts[0]
        elif platform == 'Darwin':
            result = subprocess.run(['diskutil', 'list'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if 'RPI-RP2' in line:
                    parts = line.split()
                    return f"/Volumes/{parts[-1]}"
        return None

    mount_point = find_mount_point()
    if mount_point is None:
        print("Could not find the mount point of your Sprig. Please ensure it is properly connected and try again.")
        return exit(1)
    
    print(f"Flashing firmware to your Sprig ({mount_point})...")

    with open(os.path.join(mount_point, 'pico-os.uf2'), 'wb') as f:
        f.write(firmware)

    print("Firmware flashed successfully!")

if __name__ == '__main__':
    cli()