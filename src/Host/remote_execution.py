from serial import Serial, SerialException
import settings


_seq_cmd_prompt = b'>>> '


def execute_code(code: str, device: Serial, retry_count: int = 3) -> str:
    """_summary_

    Args:
        code (str): The code to execute. This code must be ASCII-encodable.
        device (Serial): The target device on which to execute MicroPython code.

    Raises:
        UnicodeDecodeError: if the passed argument `code` is not ASCII-encodable.
        serial.SerialException: if the requested code could not be executed due to failed communication with the target
        serial device.

    Returns:
        str: The data returned from the device after executing the specified `code`.
    """
    
    # Convert input code to ASCII bytes for serial transmission
    code_bytes = bytes(code, "ASCII", "strict")

    # Attempt to transmit the code bytes to the target device
    for code_transmit_attempt in range(retry_count):
        device.write(code_bytes)
        
        # Check to see if the code was successfully transmitted to the target device
        read_data = device.read_until(expected=code_bytes)
        if read_data == code_bytes:
            # Code was transmitted successfully
            break
        
        # Code was not transmitted successfully, attempt to cancel its execution with ctrl+C (ASCII code 0x03)
        for code_cancel_attempts in range(retry_count):
            # Send a cancel signal
            device.write(b'\x03')
            
            # Listen for a new command prompt, indicating that the previous code was successfully cancelled
            read_data = device.read_until(_seq_cmd_prompt)
            if read_data == _seq_cmd_prompt:
                # Code execution was cancelled successfully
                break
            
            # Code execution could not be cancelled successfully. If all attempts to cancel code execution have been
            # exhausted, error out.
            if code_cancel_attempts == (retry_count - 1):
                raise SerialException(f"Failed to cancel the execution of the following line of code after it was incorrectly transmitted to the target device: '{code}'")
            
        # Code could not be transmitted successfully, but its execution was cancelled. If all attempts to transmit the
        # target code have been exhausted, error out,
        if code_transmit_attempt == (retry_count - 1):
            raise SerialException(f"Failed to execute the following line of code because it could not be correctly transmitted to the target device: '{code}'")
        
    # Once the code has been successfully transmitted, transmit a newline character to begin execution
    for code_execute_attempt in range(retry_count):
        device.write(b'\r')
        
        # Look for a newline character which was successfully transmitted
        read_data = device.read_until(b'\r\n')
        if read_data == b'\r\n':
            break
        
        # Code execution did not start successfully
        if code_execute_attempt == (retry_count - 1):
            raise SerialException(f"Failed to execute the following line of code because it could not begin execution: '{code}'")
    
    # Get the returned data from the target device
    read_data = device.read_until(_seq_cmd_prompt)
    
    # Make sure the returned data actually ends with a new commad prompt sequence
    if not read_data[(-1 * len(_seq_cmd_prompt)):] == _seq_cmd_prompt:
        raise SerialException(f"Failed to read all returned data after execution of the following line of code: '{code}'. This could be due to a timeout error or a transmission error. The following data was returned: '{read_data.decode("ASCII")}'")
    
    # Strip the command prompt sequence from the returned data
    read_data = read_data[:(-1 * len(_seq_cmd_prompt))]
    
    # Convert the returned data to a string and return it to the caller
    return read_data.decode("ASCII")


if __name__ == "__main__":
    import time

    settings.load_saved_settings()
    ser = Serial(port="COM3",
                 baudrate=settings.current_settings[settings._key_serial_baudrate],
                 timeout=settings.current_settings[settings._key_serial_timeout])
    
    execute_code("from machine import Pin", ser)
    execute_code("led = Pin(25, Pin.OUT)", ser)
    while True:
        execute_code("led.toggle()", ser)
        time.sleep(0.5)