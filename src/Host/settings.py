import json
import logging


_settings_file_path = "settings.json"
_key_cal_temp = "temperature calibration"
_key_cal_cell = "cell voltage calibration"
_key_last_calibrated = "last calibrated"

_default_settings = {
    _key_last_calibrated : None,
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