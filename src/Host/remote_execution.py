from serial import Serial, SerialException
import settings


_seq_cmd_prompt = b'>>> '
_board_obj_name = "board"


def _send_bytes(target_bytes: bytes, device: Serial, expected_sequence: bytes, retry_count: int = 1, expected_sequence_is_complete: bool = True) -> bool:
    for transmit_attempts in range(retry_count):
        
        # Send target bytes
        device.write(target_bytes)
        
        # Listen for the expected return sequence
        read_data = device.read_until(expected_sequence)
        if (read_data == expected_sequence and expected_sequence_is_complete) or \
            (expected_sequence in read_data and not expected_sequence_is_complete):
            # The correct return sequence was found
            return True
        
    # The target bytes could not be transmitted successfully, return False
    return False


def execute_code(code: str, device: Serial, retry_count: int = None):
    """_summary_

    Args:
        code (str): The code to execute. This code must be ASCII-encodable.
        device (Serial): The target device on which to execute MicroPython code.
        retry_count (int): The maximum number of times to attempt to execute the specified `code` before a
        `serial.SerialException` is raised. If None, defaults to the value specified in the settings file. Defaults to
        None.

    Raises:
        UnicodeDecodeError: if the passed argument `code` is not ASCII-encodable.
        serial.SerialException: if the requested code could not be executed due to failed communication with the target
        serial device.

    Returns:
        str: The data returned from the device after executing the specified `code`.
    """
    
    # Set retry_count to its default value if not specified
    retry_count = settings.current_settings[settings._key_serial_retry_count] if retry_count is None else retry_count
    
    # Convert input code to ASCII bytes for serial transmission
    code_bytes = bytes(code, "ASCII", "strict")

    for code_transmit_attempt in range(retry_count):
        
        # Attempt to transmit the code bytes to the target device
        transmit_success = _send_bytes(code_bytes, device, code_bytes)
        # If the code bytes were successfully transmitted to the target device, continue to execution
        if transmit_success:
            break
        
        # Code was not transmitted successfully, attempt to cancel its execution with ctrl-C (ASCII code 0x03)
        cancel_success = _send_bytes(b'\x03', device, b'\r\n' + _seq_cmd_prompt, retry_count)
        if not cancel_success:
            raise SerialException(f"Failed to cancel the execution of the following line of code after it was incorrectly transmitted to the target device: '{code}'")
            
        # Code could not be transmitted successfully, but its execution was cancelled. If all attempts to transmit the
        # target code have been exhausted, error out,
        if code_transmit_attempt == (retry_count - 1):
            raise SerialException(f"Failed to execute the following line of code because it could not be correctly transmitted to the target device: '{code}'")
        
    # Once the code has been successfully transmitted, transmit a newline character to begin execution
    execute_success = _send_bytes(b'\r', device, b'\r\n', retry_count)
    if not execute_success:
        raise SerialException(f"Failed to begin execution of the following line of code: '{code}'")
    
    # Get the returned data from the target device
    read_data = device.read_until(_seq_cmd_prompt)
    
    # Make sure the returned data actually ends with a new commad prompt sequence
    if not read_data[(-1 * len(_seq_cmd_prompt)):] == _seq_cmd_prompt:
        raise SerialException(f"Failed to read all returned data after execution of the following line of code: '{code}'. This could be due to a timeout error or a transmission error. The following data was returned: '{read_data.decode("ASCII")}'")
    
    # Strip the command prompt sequence from the returned data
    read_data = read_data[:(-1 * len(_seq_cmd_prompt))]
    
    # And \n\r if the returned data is non-Null
    if read_data[-2:] == b'\r\n':
        read_data = read_data[:-2]
    
    # Convert the returned data to a string and return it to the caller
    return read_data.decode("ASCII")


def execute_function(function_name: str, device: Serial, *args, **kwargs) -> str:
    """Executes a function remotely given the specified arguments

    Args:
        function_name (str): The function to execute. This function name must be ASCII-encodable.
        device (Serial): The target device on which to execute MicroPython code.

    Returns:
        str: The data returned from the device after executing the specified function.
    """
    
    # Using the given function name and arguments, construct a line of code to execute remotely
    args_str = ', '.join(str(arg) for arg in args)
    kwargs_str = ', '.join(f'{key} = {value}' for key, value in kwargs.items())
    code_to_execute = f"{function_name}({', '.join((args_str, kwargs_str)) if args_str != "" and kwargs_str != "" else args_str + kwargs_str})"
    
    # Execute the relevant code and return the result
    return execute_code(code_to_execute, device)


def reset_device(device: Serial, retry_count: int = None) -> None:
    # Set retry_count to its default value if not specified
    if retry_count is None:
        retry_count = settings.current_settings[settings._key_serial_retry_count]
        
    # Send ctrl-C (ASCII code 0x03) to exit from any line of code which has been typed or any code which is currently
    # executing
    cancel_success = _send_bytes(b'\x03', device, b'\r\n' + _seq_cmd_prompt, retry_count)
    if not cancel_success:
        raise SerialException("Failed to reset device because queued or running code could not be cancelled.")
    
    # Send ctrl-D (ASCII code 0x04) to reset the target device
    reset_success = _send_bytes(b'\x04', device, b'\r\n' + _seq_cmd_prompt, retry_count, expected_sequence_is_complete=False)
    if not reset_success:
        raise SerialException("Failed to reset device because it did not resmpond to a soft reset request.")


def init_device(device: Serial, local_adc_read_samples: int = None, local_adc_read_frequency: int = None) -> None:
    """Initializes the target device.

    Args:
        device (Serial): The target device.
        local_adc_read_samples (int): The number of samples to read from the local ADCs (5V and 24V sense) each time a
        read call is made. If None, defaults to the value specified in the settings file. Defaults to None.
        local_adc_read_frequency (int): The frequency at which to read from the local ADCs (5V and 24V sense) each time
        a read call is made. If None, defaults to the value specified in the settings file. Defaults to None.
    """
    
    # Set parameters to their default values if not specified
    local_adc_read_samples = settings.current_settings[settings._key_local_adc_read_samples] if local_adc_read_samples is None else local_adc_read_samples
    local_adc_read_frequency = settings.current_settings[settings._key_local_adc_read_frequency] if local_adc_read_frequency is None else local_adc_read_frequency
    
    # Initialize the device
    function_name = _board_obj_name + " = main"
    execute_function(function_name, device, local_adc_read_samples=local_adc_read_samples, local_adc_read_frequency=local_adc_read_frequency)
    
    
def read_ADC_5V(device: Serial) -> float:
    """Reads the SENSE_5V ADC line on the target device.

    Args:
        device (Serial): The target device.

    Returns:
        float: The nominal voltage at the SENSE_5V ADC input
    """
    
    function_name = _board_obj_name + ".read_ADC_5V"
    reading = execute_function(function_name, device)
    return float(reading)


def read_ADC_24V(device: Serial) -> float:
    """Reads the SENSE_24V ADC line on the target device.

    Args:
        device (Serial): The target device.

    Returns:
        float: The nominal voltage at the SENSE_5V ADC input
    """
    
    function_name = _board_obj_name + ".read_ADC_24V"
    reading = execute_function(function_name, device)
    return float(reading)


if __name__ == "__main__":
    import time
    from calibration import calibration

    settings.load_saved_settings()
    ser = Serial(port="COM3",
                 baudrate=settings.current_settings[settings._key_serial_baudrate],
                 timeout=settings.current_settings[settings._key_serial_timeout])
    
    # Reset the device
    execute_code("x = 3", ser)
    print(execute_code("x", ser))
    reset_device(ser)
    # This line should give a NameError, as the target device will have been reset and x will no longer be defined
    print(execute_code("x", ser))
    
    # Read the 5V and 24V rails
    init_device(ser)
    test_cal = calibration()
    print("5V rail reading:", test_cal.get_voltage_5V(read_ADC_5V(ser)), "[V]")
    print("24V rail reading:", test_cal.get_voltage_24V(read_ADC_24V(ser)), "[V]")
    
    # Blink the LED
    execute_code("from machine import Pin", ser)
    execute_code("led = Pin(25, Pin.OUT)", ser)
    while True:
        execute_code("led.toggle()", ser)
        time.sleep(0.5)