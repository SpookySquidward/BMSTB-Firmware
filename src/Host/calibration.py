import numpy as np


class calibration():
    calibration_file_name = "calibration.npy"
    
    
    def __init__(self) -> None:
        # Shape is (N_series, 1 + N_parallel, 2), where temp calibration is at index (n, 0, :) and linear regression
        # coefficients m, b are at indexes 0 and 1, respectively, in dimension 0
        self._cal_matrix = None
    
    
    @property
    def calibration_exists(self) -> bool:
        return not self._cal_matrix is None
    
    
    def get_temp_command(self, idx_cell_series: int, target_voltage: float, rail_reading_5V: float) -> int:
        # Make sure the calibration matrix exists
        if not self.calibration_exists:
            raise ValueError("No calibration found, load with use_default_calibration() or load_clibration()")
        
        # Use the calibration matrix to get the target DAC command
        target_command = target_voltage * self._cal_matrix[idx_cell_series, 0, 0] / rail_reading_5V + \
            self._cal_matrix[idx_cell_series, 0, 1]
        
        # Round the command to the nearest integer for the actual DAC command
        return round(target_command)

    
    def get_cell_command(self, idx_cell_series: int, idx_cell_parallel: int, target_voltage: float, rail_reading_5V: float) -> int:
        # Make sure the calibration matrix exists
        if not self.calibration_exists:
            raise ValueError("No calibration found, load with use_default_calibration() or load_clibration()")
        
        # Use the calibration matrix to get the target DAC command
        target_command = target_voltage * self._cal_matrix[idx_cell_series, 1 + idx_cell_parallel, 0] / rail_reading_5V + \
            self._cal_matrix[idx_cell_series, 1 + idx_cell_parallel, 1]
        
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
        
        # Create the calibration matrix for one set of parallel cells and temperature output
        cal_parallel = np.zeros((1 + cell_count_parallel, 2))
        cal_parallel[0, 0] = m_temp
        cal_parallel[1:, 0] = m_cell
        
        # Construct the full calibration matrix
        self._cal_matrix = np.repeat(cal_parallel[None, ...], cell_count_series, axis=0)


    def load_calibration(self, file_name: str = None) -> None:
        if file_name is None:
            file_name = calibration.calibration_file_name
        
        self._cal_matrix = np.load(file_name, allow_pickle=False)
        
    
    def save_calibration(self, file_name: str = None) -> None:
        if file_name is None:
            file_name = calibration.calibration_file_name
            
        np.save(file_name, self._cal_matrix, allow_pickle=False)


    def auto_calibrate(self) -> None:
        # TODO
        print("auto-calibrate routine...")


if __name__ == "__main__":
    test_cal = calibration()
    test_cal.load_calibration()
    print(test_cal.get_temp_command(17, 2.5, 5.0))
    print(test_cal.get_cell_command(17, 3, 23.8889, 5.0))
    test_cal.save_calibration()