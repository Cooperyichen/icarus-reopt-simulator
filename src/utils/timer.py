"""
Implements a simple timer that expires after a timeout value. When it expires,
it runs a provided callback function.

Example Usage
-------------
import simpy

def timeout_handler(timer_id):
    print(f"Timer {timer_id} expired!")

env = simpy.Environment()
timer = Timer(env, timer_id=1, timeout_callback=timeout_handler, rto=5)
env.run(until=10)  # Run the simulation for 10 units of time

This will output:
Timer 1 expired!

Author:
-------
zineb.garroussi@polymtl.ca
"""

class Timer:
    """A simple timer that expires after a timeout value. When it expires, it runs a
    provided callback function.

    Parameters
    ----------
    env: simpy.Environment
        The simulation environment.
    timer_id: int
        The id of this timer, used as a parameter when the timeout
        callback function is called.
    timeout_callback: function
        The callback function that runs when the timer expires.
    timeout: float
        The timeout value.
    """

    def __init__(self, env, timer_id, timeout_callback, rto):
        """ Initializes the timer with the simulation environment, timer ID, callback, and timeout value.
        
        Parameters
        ----------
        env : simpy.Environment
            The simulation environment.
        timer_id : int
            The ID of the timer.
        timeout_callback : function
            The callback function to be called when the timer expires.
        rto : float
            The timeout value after which the timer expires.
        """
        self.env = env  # Simulation environment
        self.timer_id = timer_id  # ID of the timer
        self.timeout_callback = timeout_callback  # Callback function to run when the timer expires
        self.rto = rto  # Timeout value
        self.timer_started = self.env.now  # Time when the timer starts
        self.timer_expiry = self.timer_started + rto  # Time when the timer will expire
        self.stopped = False  # Flag to check if the timer is stopped
        self.action = env.process(self.run())  # Start the timer process

    def run(self):
        """The generator function used in simulations."""
        while True:
            if self.env.now < self.timer_expiry:
                # Wait until the timer expires
                yield self.env.timeout(self.timer_expiry - self.env.now)
            
            if not self.stopped:
                # If the timer is not stopped, call the timeout callback
                self.timeout_callback(self.timer_id)
            else:
                # If the timer is stopped, exit the loop
                return

    def stop(self):
        """Stopping the timer."""
        self.stopped = True  # Set the stopped flag to True
        self.timer_expiry = self.env.now  # Update the expiry time to the current time

    def restart(self, revised_rto, start_time=0):
        """Restarting the timer with a new rto value.
        
        Parameters
        ----------
        revised_rto : float
            The new timeout value.
        start_time : float, optional
            The new start time for the timer. Defaults to the current time.
        """
        self.rto = revised_rto  # Update the timeout value

        if start_time == 0:
            self.timer_started = self.env.now  # Reset the start time to the current time
        else:
            self.timer_started = start_time  # Set the start time to the provided value

        self.timer_expiry = self.timer_started + revised_rto  # Update the expiry time







