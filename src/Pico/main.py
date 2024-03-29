from machine import ADC, Pin, Timer, I2C
import i2c_devices

class main:
    def __init__(self, local_adc_read_samples: int, local_adc_read_frequency: int, i2c_frequency: int):
        # Pin definitions
        self.pin_sense_24V = Pin(27)
        self.adc_sense_24V = ADC(self.pin_sense_24V)
        self.pin_sense_5V = Pin(26)
        self.adc_sense_5V = ADC(self.pin_sense_5V)
        
        self.pin_led = Pin(25, Pin.OUT)
        
        self.pin_scl = Pin(21, Pin.OUT)
        self.pin_sda = Pin(20, Pin.OUT)
        self.i2c = I2C(0, scl = self.pin_scl, sda = self.pin_sda, freq = i2c_frequency)
        
        # ADC read information
        self.local_adc_read_samples = local_adc_read_samples
        self.local_adc_read_frequency = local_adc_read_frequency
        
        # Activity LED timer
        self.status_LED_timer = None
        self.set_status_LED(False)


    def _read_ADC(self, adc: ADC):
        # Take self.adc_read_samples samples from the specified adc port and return the scaled mean (0-1 float)
        adc_counts = 0
        samples_remaining = self.local_adc_read_samples
        
        # Timer callback to take individual ADC samples. Once all samples have been taken, the timer object will be
        # deinitialized
        def timer_callback(timer):
            nonlocal adc_counts, samples_remaining
            
            # Take an ADC sample
            adc_counts = adc_counts + adc.read_u16()
            
            # One sample was taken, decrement the number of remaining samples
            samples_remaining = samples_remaining - 1
            
            # If no more samples are needed, deinitialize the timer
            if samples_remaining == 0:
                timer.deinit()
                
        # Create the timer object and begin acquiring ADC readings
        Timer(-1).init(mode=Timer.PERIODIC, freq=self.local_adc_read_frequency, callback=timer_callback)
        
        # Wait until all samples have been taken
        while samples_remaining > 0:
            pass
        
        # Once all samples have been taken successfully, return their scaled mean
        return (adc_counts * 3.0) / (self.local_adc_read_samples * 65535)


    def read_ADC_5V(self):
        return self._read_ADC(self.adc_sense_5V)


    def read_ADC_24V(self):
        return self._read_ADC(self.adc_sense_24V)
    
    
    def set_status_LED(self, blink_LED: bool, blink_rate: int = None):
        # If blink_LED is True, start blinking at blink_rate
        if blink_LED:
            def blink_callback(_):
                self.pin_led.toggle()
                
            self.status_LED_timer = Timer(-1)
            self.status_LED_timer.init(mode=Timer.PERIODIC, freq=blink_rate*2, callback=blink_callback)
            
        # Otherwise, clear the timer and leave the LED on to indicate power present
        else:
            if self.status_LED_timer is not None:
                self.status_LED_timer.deinit()
                self.status_LED_timer = None
                
            self.pin_led.high()