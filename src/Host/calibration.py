import numpy as np
import settings
import logging
from datetime import datetime, UTC


class calibration():
    def __init__(self) -> None:
        # Shape is (N_series, N_parallel, 2), where linear regression coefficients m, b are at indexes 0 and 1,
        # respectively, in dimension 2
        self._cell_cal_matrix = None
        
        # Shape is (N_series, 2), where linear regression coefficients m, b are at indexes 0 and 1, respectively, in
        # dimension 1
        self._temp_cal_matrix = None
        
        # Load the calibration profile stored in settings
        self.load_calibration()
    
    
    @property
    def calibration_exists(self) -> bool:
        return not (self._cell_cal_matrix is None or self._temp_cal_matrix is None)
    
    
    def get_temp_command(self, idx_cell_series: int, target_voltage: float, rail_reading_5V: float) -> int:
        # Make sure the calibration matrixes exists
        if not self.calibration_exists:
            raise ValueError("No calibration found, load with use_default_calibration() or load_calibration()")
        
        # Use the calibration matrix to get the target DAC command
        cal_coefficients = self._temp_cal_matrix[idx_cell_series, :]
        target_command = target_voltage * cal_coefficients[0] / rail_reading_5V + cal_coefficients[1]
        
        # Round the command to the nearest integer for the actual DAC command
        return round(target_command)

    
    def get_cell_command(self, idx_cell_series: int, idx_cell_parallel: int, target_voltage: float, rail_reading_5V: float) -> int:
        # Make sure the calibration matrixes exists
        if not self.calibration_exists:
            raise ValueError("No calibration found, load with use_default_calibration() or load_calibration()")
        
        # Use the calibration matrix to get the target DAC command
        cal_coefficients = self._cell_cal_matrix[idx_cell_series, idx_cell_parallel, :]
        target_command = target_voltage * cal_coefficients[0] / rail_reading_5V + cal_coefficients[1]
        
        # Round the command to the nearest integer for the actual DAC command
        return round(target_command)

    
    def use_default_calibration(self,
                                cell_count_series: int = 18,
                                cell_count_parallel: int = 4,
                                cell_amp_R_L: float = 18.,
                                cell_amp_R_H: float = 68.,
                                DAC_bits_cell: int = 12,
                                DAC_bits_temp: int = 12) -> None:
        
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


    def load_calibration(self) -> None:
        """Loads cell and temp calibration data from the settings module. This requires settings to be initialized with
        `load_saved_settings()` or `load_default_settings()`.
        """
        
        # Cell calibration
        new_cell_cal_matrix = settings.current_settings[settings._key_cal_cell]
        try:
            self._cell_cal_matrix = np.array(new_cell_cal_matrix).astype(float)
        except ValueError as e:
            logging.info(f"Could not create cell calibration matrix due to the following error: '{e}'. Defaulting to no caolibration.")
            self._cell_cal_matrix = None
        
        # Temp calibration
        new_temp_cal_matrix = settings.current_settings[settings._key_cal_temp]
        try:
            self._temp_cal_matrix = np.array(new_temp_cal_matrix)
        except ValueError as e:
            logging.info(f"Could not create temp calibration matrix due to the following error: '{e}'. Defaulting to no caolibration.")
            self._temp_cal_matrix = None
        
    
    def save_calibration(self) -> None:
        """Saves cell and temp calibration data to the settings module. `settings.save_current_settings()` must be
        called to actually save the calibration data to the disk.
        """
        
        settings.current_settings[settings._key_cal_cell] = self._cell_cal_matrix.tolist()
        settings.current_settings[settings._key_cal_temp] = self._temp_cal_matrix.tolist()
        settings.current_settings[settings._key_last_calibrated] = str(datetime.now(UTC))


    def auto_calibrate(self) -> None:
        # TODO
        print("auto-calibrate routine...")


if __name__ == "__main__":
    settings.load_saved_settings()
    
    test_cal = calibration()
    test_cal.use_default_calibration()
    print(test_cal.get_temp_command(17, 2.5, 5.0))
    print(test_cal.get_cell_command(17, 3, 23.8889, 5.0))
    test_cal.save_calibration()
    
    settings.save_current_settings()