To use the script create an .mxpy file the contains instructions for your hysteresis. Install mumax3 and add it to your
PATH as well as python. Run
    python AdaptiveHysteresis.py [filename] (mumax3arguments)
Not that the AdaptiveHysteresis.py script will use the directory from which it is executed as a temporary storage for
magnetization files. Currently the AdaptiveHysteresis.py should only be executed from the same directory as the .mxpy
file.

Some examples are included in the /example folder including output.

To run the example.mxpy script, copy the AdaptiveHysteresis.py script to the /example folder and run from there run
    python AdaptiveHysteresis.py example.mxpy
This will create an example.mx3 file, run it and configure it for an optimized hysteresis according to the parameters
listed at the end of example.mxpy. The evaluation should take about 5 minutes in total and is too fast to be monitored
with the mumax3 web interface.