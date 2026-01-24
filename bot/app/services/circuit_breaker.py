import time
import logging
from enum import Enum

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Service down, fail fast
    HALF_OPEN = "HALF_OPEN" # Testing recovery

class CircuitBreaker:
    """
    Prevents cascading failures by stopping calls to a failing service.
    """
    _instances = {}

    def __new__(cls, name, failure_threshold=5, recovery_timeout=60):
        if name not in cls._instances:
            instance = super(CircuitBreaker, cls).__new__(cls)
            instance.name = name
            instance.failure_threshold = failure_threshold
            instance.recovery_timeout = recovery_timeout
            instance.failure_count = 0
            instance.last_failure_time = 0
            instance.state = CircuitState.CLOSED
            cls._instances[name] = instance
        return cls._instances[name]

    def call(self, func, *args, **kwargs):
        """Execute a function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logging.info(f"🔄 Circuit Breaker [{self.name}] moving to HALF_OPEN state...")
                self.state = CircuitState.HALF_OPEN
            else:
                logging.warning(f"🚫 Circuit Breaker [{self.name}] is OPEN. Fast-failing request.")
                return None

        try:
            result = func(*args, **kwargs)
            # If we are here, the call succeeded (didn't raise exception)
            if self.state == CircuitState.HALF_OPEN:
                logging.info(f"✅ Circuit Breaker [{self.name}] recovered! Closing circuit.")
                self.reset()
            return result
        except Exception as e:
            self.record_failure()
            logging.error(f"⚠️ Circuit Breaker [{self.name}] recorded failure: {e}")
            raise e

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            logging.critical(f"🚨 Circuit Breaker [{self.name}] TRIPPED! State is now OPEN for {self.recovery_timeout}s.")
            self.state = CircuitState.OPEN

    def reset(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

def get_breaker(name):
    return CircuitBreaker(name)
