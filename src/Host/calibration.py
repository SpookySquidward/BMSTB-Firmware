import numpy as np
import settings
import logging
from datetime import datetime, UTC
import humanize


class calibration():
    def __init__(self) -> None:
        # Shape is (N_series, N_parallel, 2), where linear regression coefficients m, b are at indexes 0 and 1,
        # respectively, in dimension 2
        self._cell_cal_matrix = None
        
        # Shape is (N_series, 2), where linear regression coefficients m, b are at indexes 0 and 1, respectively, in
        # dimension 1
        self._temp_cal_matrix = None
        
        # Shapes are (2), where linear regression coefficients m, b are at indexes 0 and 1, respectively
        self._sense_5V_cal = None
        self._sense_24V_cal = None
        
        # Load the calibration profile stored in settings
        self.load_calibration()
    
    
    @property
    def calibration_loaded(self) -> bool:
        return not (self._cell_cal_matrix is None or
                    self._temp_cal_matrix is None or
                    self._sense_5V_cal is None or
                    self._sense_24V_cal is None)
    
    
    def get_temp_command(self, idx_cell_series: int, target_voltage: float, rail_reading_5V: float) -> int:
        # Make sure the calibration matrixes exists
        if not self.calibration_loaded:
            raise ValueError("No calibration found, load with use_default_calibration() or load_calibration()")
        
        # Use the calibration matrix to get the target DAC command
        cal_coefficients = self._temp_cal_matrix[idx_cell_series, :]
        target_command = target_voltage * cal_coefficients[0] / rail_reading_5V + cal_coefficients[1]
        
        # Round the command to the nearest integer for the actual DAC command
        return round(target_command)

    
    def get_cell_command(self, idx_cell_series: int, idx_cell_parallel: int, target_voltage: float, rail_reading_5V: float) -> int:
        # Make sure the calibration matrixes exists
        if not self.calibration_loaded:
            raise ValueError("No calibration found, load with use_default_calibration() or load_calibration()")
        
        # Use the calibration matrix to get the target DAC command
        cal_coefficients = self._cell_cal_matrix[idx_cell_series, idx_cell_parallel, :]
        target_command = target_voltage * cal_coefficients[0] / rail_reading_5V + cal_coefficients[1]
        
        # Round the command to the nearest integer for the actual DAC command
        return round(target_command)


    def get_voltage_5V(self, sense_5V_ADC_reading: float) -> float:
        # Make sure the calibration matrixes exists
        if not self.calibration_loaded:
            raise ValueError("No calibration found, load with use_default_calibration() or load_calibration()")
        
        # Calibrate the ADC reading
        return self._sense_5V_cal[0] * sense_5V_ADC_reading + self._sense_5V_cal[1]
    
    
    def get_voltage_24V(self, sense_24V_ADC_reading: float) -> float:
        # Make sure the calibration matrixes exists
        if not self.calibration_loaded:
            raise ValueError("No calibration found, load with use_default_calibration() or load_calibration()")
        
        # Calibrate the ADC reading
        return self._sense_24V_cal[0] * sense_24V_ADC_reading + self._sense_24V_cal[1]

    
    def use_default_calibration(self,
                                cell_count_series: int = 18,
                                cell_count_parallel: int = 4,
                                cell_amp_R_L: float = 18.,
                                cell_amp_R_H: float = 68.,
                                DAC_bits_cell: int = 12,
                                DAC_bits_temp: int = 12,
                                sense_5V_R_L: float = 1.8,
                                sense_5V_R_H: float = 2.2,
                                sense_24V_R_L: float = 1.,
                                sense_24V_R_H: float = 10.) -> None:
        
        # The temperature DAC slope is determined only by the number of DAC bits
        m_temp = 2 ** DAC_bits_temp
        
        # The cell DAC slope is determined by the number of DAC bits and by the op amp resistors
        m_cell = (2 ** DAC_bits_cell) / (1 + cell_amp_R_H / cell_amp_R_L)
        
        # Create the calibration matrixes for one set of parallel cells and temperature output
        cal_parallel_cell = np.zeros((cell_count_parallel, 2))
        cal_parallel_cell[:, 0] = m_cell
        cal_single_temp = np.zeros((2))
        cal_single_temp[0] = m_temp
        
        # Construct the full calibration matrixes
        self._cell_cal_matrix = np.repeat(cal_parallel_cell[None, ...], cell_count_series, axis=0)
        self._temp_cal_matrix = np.repeat(cal_single_temp[None, ...], cell_count_series, axis=0)
        
        # Add calibrations for 5V and 24V rail monitor
        self._sense_5V_cal = np.array([(1 + sense_5V_R_H / sense_5V_R_L), 0])
        self._sense_24V_cal = np.array([(1 + sense_24V_R_H / sense_24V_R_L), 0])


    def _get_calibration_matrix(setting_key: str) -> np.array(float):
        new_cal_matrix = settings.current_settings[setting_key]
        if not new_cal_matrix == settings._default_settings[setting_key]:
            try:
                new_cal_matrix = np.array(new_cal_matrix).astype(float)
            except ValueError as e:
                logging.info(f"Could not create {setting_key} calibration matrix due to the following error: '{e}'. Defaulting to no calibration.")
                new_cal_matrix = None
        
        return new_cal_matrix


    def load_calibration(self) -> None:
        """Loads cell, temp, and rail monitor calibration data from the settings module. This requires settings to be
        initialized with `load_saved_settings()` or `load_default_settings()`.
        """
        
        self._cell_cal_matrix = calibration._get_calibration_matrix(settings._key_cal_cell)
        self._temp_cal_matrix = calibration._get_calibration_matrix(settings._key_cal_temp)
        self._sense_5V_cal = calibration._get_calibration_matrix(settings._key_cal_5V)
        self._sense_24V_cal = calibration._get_calibration_matrix(settings._key_cal_24V)
        
        
    
    def save_calibration(self) -> None:
        """Saves cell and temp calibration data to the settings module. `settings.save_current_settings()` must be
        called to actually save the calibration data to the disk.
        """
        
        settings.current_settings[settings._key_cal_cell] = self._cell_cal_matrix.tolist()
        settings.current_settings[settings._key_cal_temp] = self._temp_cal_matrix.tolist()
        settings.current_settings[settings._key_cal_5V] = self._sense_5V_cal.tolist()
        settings.current_settings[settings._key_cal_24V] = self._sense_24V_cal.tolist()
        settings.current_settings[settings._key_last_calibrated] = str(datetime.now(UTC))
        
    
    def time_since_last_calibration(self) -> str:
        try:
            # Give a human-readable time since last calibration
            last_calibrated_time = datetime.fromisoformat(settings.current_settings[settings._key_last_calibrated])
            time_since_last_calibrated = datetime.now(UTC) - last_calibrated_time
            return humanize.naturaldelta(time_since_last_calibrated)
        except:
            # These exceptions may come from settings, datetime, or humanize, and really should be enumerated; but I
            # can't be bothered at the moment
            return None


    def auto_calibrate(self) -> None:
        # TODO
        print("auto-calibrate routine...")
        self.use_default_calibration()


if __name__ == "__main__":
    settings.load_saved_settings()
    
    test_cal = calibration()
    test_cal.use_default_calibration()
    print(test_cal.time_since_last_calibration())
    print(test_cal.get_temp_command(17, 2.5, 5.0))
    print(test_cal.get_cell_command(17, 3, 23.8889, 5.0))
    test_cal.save_calibration()
    
    settings.save_current_settings()