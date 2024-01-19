import json
import logging


_settings_file_path = "settings.json"
_key_cells_series = "series cell count"
_key_cells_parallel = "parallel cell count"
_key_serial_baudrate = "serial baudrate"
_key_serial_timeout = "serial timeout (s)"
_key_serial_retry_count = "serial transmission retry count"
_key_status_LED_blink_rate = "Status LED blink rate (Hz)"
_key_local_adc_read_samples = "5V/24V rail monitor samples"
_key_local_adc_read_frequency = "5V/24V rail monitor sample frequency (Hz)"
_key_i2c_bus_frequency = "I2C bus clock frequency (Hz)"
_key_last_calibrated = "last calibrated (UTC)"
_key_cal_5V = "5V rail monitor calibration"
_key_cal_24V = "24V rail monitor calibration"
_key_cal_temp = "temperature calibration"
_key_cal_cell = "cell voltage calibration"

_default_settings = {
    _key_cells_series: 18,
    _key_cells_parallel: 4,
    _key_serial_baudrate: 115200,
    _key_serial_timeout: 1.0,
    _key_serial_retry_count: 3,
    _key_status_LED_blink_rate: 5,
    _key_local_adc_read_samples: 1024,
    _key_local_adc_read_frequency: 25000,
    _key_i2c_bus_frequency: 400000,
    _key_last_calibrated : None,
    _key_cal_5V: None,
    _key_cal_24V: None,
    _key_cal_temp: None,
    _key_cal_cell: None,
}

# Write to this dict using the above keys elsewhere in code to update settings
current_settings = {}


def save_current_settings():
    with open(_settings_file_path, "w") as f:
        json.dump(current_settings, f, indent=4)


def load_saved_settings():
    # Create a sew set of global settings which uses the defaults for any settings not specified in the JSON
    new_current_settings = _default_settings.copy()
    
    # Look for overwritten settings in the JSON file
    try:
        with open(_settings_file_path, "r") as f:
            loaded_settings = json.load(f)
            
            # Check to make sure the loaded settings are of a dict format
            if not type(loaded_settings) is dict:
                logging.info(f"Attempted to load settings.json, but got object of type {type(loaded_settings)} instead of dict.")
                
            else:
                # Apply any specified settings
                for loaded_setting_key in loaded_settings.keys():
                    new_current_settings[loaded_setting_key] = loaded_settings[loaded_setting_key]
    
    except IOError:
        logging.info("Attempted to load settings.json, but an IOError was raised. Reverting to default settings.")
    
    except json.decoder.JSONDecodeError:
        logging.info("Attempted to load settings.json, but a JSONDecodeError was raised. Reverting to default settings.")
    
    # Apply the new current settings
    global current_settings
    current_settings = new_current_settings


def load_default_settings():
    global current_settings
    current_settings = _default_settings.copy()