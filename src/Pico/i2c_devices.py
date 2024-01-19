# Lightweight interface for the PCA9539 GPIO expander and MCP4728 DAC
from machine import I2C


def _changebit(bitmap: bytes, bit: int, value: int):
    if value == 0:
        return int(bitmap[0] & ~(1 << bit)).to_bytes(1, "big")
    elif value == 1:
        return (int(bitmap[0]) | (1 << bit)).to_bytes(1, "big")
    else:
        raise ValueError("Illegal value " + str(value))


class PCA9539:
    def __init__(self, i2c: I2C, address: int = 0x74):
        self.i2c = i2c
        self.address = address
    
    
    def set_pin(self, pin: int, value: int):
        # Ensure the specified pin is valid
        if not ((0 <= pin and pin <= 7) or (10 <= pin and pin <= 17)):
            raise ValueError("Illegal pin number " + str(pin) + " specified!")
        
        # Get pin and bank offsets for address manipulation
        pin_offset = pin % 10
        bank_offset = pin >= 10
        
        # Get the current output and configuration port states for the given bank
        output_port_address = 0x03 if bank_offset else 0x02
        configuration_port_address = 0x07 if bank_offset else 0x06
        current_output_port = self.i2c.readfrom_mem(self.address, output_port_address, 1)
        current_configuration_port = self.i2c.readfrom_mem(self.address, configuration_port_address, 1)
        
        # Set the output to high if value is 1, or low if it is 0
        new_output_port = _changebit(current_output_port, pin_offset, int(value))
        self.i2c.writeto_mem(self.address, output_port_address, new_output_port)
        
        # Set the specified pin to be anoutput pin
        new_configuration_port = _changebit(current_configuration_port, pin_offset, 0)
        self.i2c.writeto_mem(self.address, configuration_port_address, new_configuration_port)