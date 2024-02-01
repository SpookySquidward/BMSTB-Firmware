import main
import time
from machine import Pin
import micropython

micropython.alloc_emergency_exception_buf(100)

_default_MCP_address = 0b1100000


# In order to program the MCP DACs' I2C addresses correctly, an external NPN transistor must temporarily be soldered to
# the Pi Pico. This lets the Pico pull the LDAC line low at the proper time without being damaged by 5V logic levels
# present on the line. Connect a general-purpose NPN transistor, such as a 2N3904, as-follows:
#   - Collector: connect to the LDAC line of whichever MCP device you are programming. I recommend adding a probe wire
#     to the transistor pin to make connection to the relevant LDAC signal easy.
#   - Emitter: connect to GND on the board. The Pico's pins themselves act as convenient solder points.
#   - Base: connect to the Pico GPIO pin specified below. Make sure this GPIO isn't being used for anything else!
transistor_base_pin = 11

# The main codebase expects the following mappings for MCP chips to I2C addresses, and you should program the MCPs as-
# such:
#   U10_1: 0x61
#   U10_2: 0x62
#   U10_3: 0x63
#   U10_4: 0x64
#   U10_5: 0x65
#   U10_6: 0x66
#   U10_7: 0x67


def update_MCP_address(board: main.main, current_address: int, new_address: int):
    # Make sure the current and new addresses are both valid
    for address in (current_address, new_address):
        if not (address >= _default_MCP_address and address <= _default_MCP_address + 7):
            raise ValueError("Illegal address specified: " + str(address))
        
    # Set up the transistor base pin as an output to control the LDAC signal
    pin_inv_LDAC = Pin(transistor_base_pin, Pin.OUT)
    pin_inv_LDAC.low()
    
    # Construct the command which will be used to update the address
    # See Figure 5-11 of the MCP4728 datasheet for details
    update_command = bytes([
        0b01100001 + ((current_address - _default_MCP_address) << 2),
        0b01100010 + ((new_address - _default_MCP_address) << 2),
        0b01100011 + ((new_address - _default_MCP_address) << 2),
        0b11111111])
    
    # Create a callback function which will prompt the user to pull the LDAC pin low when needed
    clock_cycles_remaining = 18
    def callback_LDAC(interrupt_pin: Pin):
        # Count the current clock cycle
        nonlocal clock_cycles_remaining, pin_inv_LDAC
        clock_cycles_remaining = clock_cycles_remaining - 1
        
        # If the required number of clock cycles have been counted, pull the LDAC pin low
        if clock_cycles_remaining == 0:
            pin_inv_LDAC.high()
            interrupt_pin.irq(handler=None)
            
    # Register the callback function
    board.pin_scl.irq(handler=callback_LDAC, trigger=Pin.IRQ_FALLING, hard=True)
    time.sleep_ms(10)
    
    # Execute the update command
    input("Please connect the collector of the external NPN transistor to the target device's LDAC pin. When you have done this, press Enter to continue...")
    board.i2c.writeto(current_address, update_command)
    
    
if __name__ == "__main__":
    # Set up I2C and scan for current devices
    board = main.main(local_adc_read_samples = 10, local_adc_read_frequency = 10, i2c_frequency = 10000)
    current_devices = board.i2c.scan()
    print(f"The following device addresses are currently in use: {list(hex(address) for address in current_devices)}")
    
    # Update the address of a user-specified device
    current_address = int(input(f"Enter current MCP I2C address (default is {hex(_default_MCP_address)}, range is [{hex(_default_MCP_address)}, {hex(_default_MCP_address + 7)}]): "))
    new_address = int(input(f"Enter new MCP I2C address (range is [{hex(_default_MCP_address)}, {hex(_default_MCP_address + 7)}]): "))
    update_MCP_address(board, current_address, new_address)
    
    # Check to see if the device's I2C address was successfully updated
    new_devices = board.i2c.scan()
    print(f"The following device addresses are now detected: {list(hex(address) for address in new_devices)}")
    if not (new_address in current_devices):
        if new_address in new_devices:
            print(f"The target MCP's I2C address was successfully updated to {hex(new_address)}.")
        else:
            print(f"The target MCP's I2C address was not successfully updated. This can happen if multiple devices share the same current I2C address ({hex(current_address)}); try updating the I2C address of one of those devices first.")
