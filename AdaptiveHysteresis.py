import csv
import math
import os
import os.path
import re
import subprocess
import sys
import time
from math import log10, floor
from multiprocessing import Lock
from os import devnull
from shutil import copy2

globallock = Lock()
scriptfileName = ""
timeColumnIndex = 0
mxColumnIndex = 1
myColumnIndex = 2
mzColumnIndex = 3
bxColumnIndex = 4
byColumnIndex = 5
bzColumnIndex = 6

fieldsteps = []

# Default values
nLoops = 20
Bmin = -2.0
Bmax = 2.0
BdirectionTheta = 0.5 * math.pi
BdirectionPhi = 0.0
BminStep = 0.0001
BinitialStep = 0.5
MmaxDiff = 0.01  # BminStep is more powerful than MmaxDiff
scriptBase = ""
saveM = False


def generateFieldsteps(fieldsteps, loadM, contIndex, save):
    re = "//" + str(fieldsteps)
    re = re + "\n"
    re = re + loadM
    re = re + "\n"
    print("CONT_INDEX = " + str(contIndex) + "---> FIELDPOS = " + str(fieldsteps[contIndex]))
    for fieldstep in range(contIndex, len(fieldsteps) - 1):
        re = re + "\nB_ext = vector("
        re = re + "(" + str(fieldsteps[fieldstep]) + ") * " + str(
            math.cos(BdirectionPhi) * math.sin(BdirectionTheta)) + ", "
        re = re + "(" + str(fieldsteps[fieldstep]) + ") * " + str(
            math.sin(BdirectionPhi) * math.sin(BdirectionTheta)) + ", "
        re = re + "(" + str(fieldsteps[fieldstep]) + ") * " + str(math.cos(BdirectionTheta)) + ")"
        re = re + "\n"
        re = re + "relax()"
        re = re + "\n"
        re = re + "tableSave()"
        re = re + "\n"
        if save:
            re = re + "save(m)"
            re = re + "\n"
    return re


def readFile(name):
    # Use al globals as writable globals in this function
    global saveM
    global nLoops
    global Bmin
    global Bmax
    global BdirectionTheta
    global BdirectionPhi
    global BminStep
    global BinitialStep
    global MmaxDiff  # BminStep is more powerful than MmaxDiff

    global scriptBase
    f = open(name, 'r')
    # print(f)
    # print("\n\n\n")
    s = f.read()
    scriptBase = s.split("hysteresis{")[0]
    pattern = re.compile("hysteresis{.*}", re.DOTALL)
    match = pattern.search(s)

    instructions = ""
    if match:
        instructions = match.group()
    else:
        # TODO: check for FORK if its not Hysteresis
        sys.exit(0)
    instructions = "\n".join(re.split("[#].*\n", instructions))

    pattern = re.compile("saveM.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        saveMtmp = int(match.group().split("=")[1].split(";")[0])
        if saveMtmp == 0:
            saveM = False
        else:
            saveM = True

    pattern = re.compile("nLoops.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        nLoops = int(match.group().split("=")[1].split(";")[0])

    pattern = re.compile("Bmin.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        Bmin = float(match.group().split("=")[1].split(";")[0])

    pattern = re.compile("BdirectionTheta.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        BdirectionTheta = float(match.group().split("=")[1].split(";")[0])

    pattern = re.compile("BdirectionPhi.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        BdirectionPhi = float(match.group().split("=")[1].split(";")[0])

    pattern = re.compile("Bmax.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        Bmax = float(match.group().split("=")[1].split(";")[0])

    pattern = re.compile("BminStep.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        BminStep = float(match.group().split("=")[1].split(";")[0])

    pattern = re.compile("BinitialStep.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        BinitialStep = float(match.group().split("=")[1].split(";")[0])

    pattern = re.compile("MmaxDiff.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        MmaxDiff = float(match.group().split("=")[1].split(";")[0])
    # print(instructions)
    processfile(name)


def processfile(name):
    global fieldsteps
    global scriptfileName
    filename = ".".join(name.split(".")[0:-1])
    scriptfileName = filename + ".mx3"
    fieldsteps = []

    fieldstep = math.floor(Bmin / BinitialStep)

    while fieldstep <= math.floor(Bmax / BinitialStep):
        fieldsteps.append(round_to_n(fieldstep * BinitialStep, 4))
        fieldstep += 1
    fieldstep -= 2
    while fieldstep >= math.floor(Bmin / BinitialStep):
        fieldsteps.append(round_to_n(fieldstep * BinitialStep, 4))
        fieldstep -= 1
    writeScript("", 0)


def writeScript(loadM, contIndex):
    f = open(scriptfileName, 'w')
    outputstring = scriptBase
    outputstring = outputstring + generateFieldsteps(fieldsteps, loadM, contIndex, True)
    f.write(outputstring)


def writeScriptLoop(n):
    f = open(scriptfileName, 'w')
    outputstring = scriptBase
    outputstring = outputstring + "\n"
    outputstring = outputstring + "for i := 0; i < " + str(n) + "; i++ {"
    outputstring = outputstring + generateFieldsteps(fieldsteps, "", 0, saveM)
    outputstring = outputstring + "\n}"
    f.write(outputstring)


def round_to_n(x, n):
    if x == 0:
        return 0
    return round(x, -int(floor(log10(abs(x / (math.pow(10, n - 1)))))))


def minus(x, y):
    return [x[0] - y[0], x[1] - y[1], x[2] - y[2]]


def norm(x):
    return math.sqrt(dot3D(x, x))


def dot3D(x, y):
    return (x[0] * y[0]) + (x[1] * y[1]) + (x[2] * y[2])


# Unit Vector in B-Direction
def eB():
    return [math.cos(BdirectionPhi) * math.sin(BdirectionTheta), math.sin(BdirectionPhi) * math.sin(BdirectionTheta),
            math.cos(BdirectionTheta)]


def monitorTable(mumaxoutput):
    success = True
    while True:
        try:
            if success == False:
                return index
            magne = []
            field = []
            index = 0
            time.sleep(5)
            f = open((".".join(scriptfileName.split(".")[0:-1])) + ".out\\table.txt", 'r')
            with f as csvfile:
                plots = csv.reader(csvfile, delimiter='\t')
                next(plots, None)
                for row in plots:
                    magne.append([float(row[mxColumnIndex]), float(row[myColumnIndex]), float(row[mzColumnIndex])])
                    field.append([float(row[bxColumnIndex]), float(row[byColumnIndex]), float(row[bzColumnIndex])])

            mtmp = magne[0]
            btmp = field[0]
            for i in range(0, len(magne) - 1):
                m = magne[i]
                b = field[i]
                # print(norm(minus(btmp, b)))
                if (abs(dot3D(minus(mtmp, m), eB())) < MmaxDiff) | (round_to_n(norm(minus(btmp, b)), 3) <= BminStep):
                    # print("Step: " + str(round_to_n(norm(minus(btmp, b)), 3)) + ", " + str(
                    #    norm(minus(btmp, b))) + "Minstep: " + str(BminStep))
                    mtmp = m
                    btmp = b
                else:
                    print("Step: " + str(round_to_n(norm(minus(btmp, b)), 3)) + ", (" + str(
                        norm(minus(btmp, b))) + ") Minstep: " + str(BminStep))
                    print("fail")
                    success = False
                    index = i
                    break
        except AttributeError as err:
            print("AttributeError: {0}".format(err))
        except ValueError as err:
            print("ValueError: {0}".format(err))
        except TypeError as err:
            print("TypeError: {0}".format(err))
        except IndexError as err:
            print("IndexError: {0}".format(err))
        except:
            print("Error: No Error. Continue ...", sys.exc_info()[0])
        if not (mumaxoutput.poll() == None):
            print("The Simulation is over.")
            # TODO: terminate everything
            return index


def checkfor(args):
    """Make sure that a program necessary for using this script is
    available.

    Arguments:
    args -- list of commands to pass to subprocess.call.
    """
    if isinstance(args, str):
        args = args.split()
    try:
        with open(devnull, 'w') as f:
            subprocess.call(args, stderr=subprocess.STDOUT, stdout=f)
    except:
        print("Required program '{}' not found! exiting.".format(args[0]))
        sys.exit(1)


def getMFilenameFromIndex(index):
    # m000000.ovf
    re = "m"
    if index <= 9:
        re = re + "00000"
    else:
        if index <= 99:
            re = re + "0000"
        else:
            if index <= 999:
                re = re + "000"
            else:
                if index <= 9999:
                    re = re + "00"
                else:
                    if index <= 99999:
                        re = re + "0"
    re = re + str(index) + ".ovf"
    return re


def adaptLoop(args):
    index = 1
    fieldstepindex = 0
    while index != 0:
        time.sleep(10)
        mumaxoutput = subprocess.Popen(args)  # , shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(10)

        index = monitorTable(mumaxoutput)
        print("Terminating Thread with mumax3!!!")
        mfilename = ""
        if index > 1:
            mfilename = getMFilenameFromIndex(index - 1)
            fieldstepindex = fieldstepindex + index - 1
        else:
            mfilename = getMFilenameFromIndex(0)
            fieldstepindex = fieldstepindex + index
        print("--------------------------->" + mfilename)

        src = (".".join(scriptfileName.split(".")[0:-1])) + ".out\\" + str(mfilename)
        dest = os.path.dirname(__file__)
        copy2(src, dest)
        time.sleep(10)
        mumaxoutput.kill()
        mumaxoutput.wait()

        upper = fieldsteps[fieldstepindex + 1]
        lower = fieldsteps[fieldstepindex]
        slope = upper - lower
        print("FIELD_STEP TOO LARGE BETWEEN " + str(upper) + " AND " + str(lower))
        for i in range(1, 10):
            fieldsteps.insert(fieldstepindex + (i), round_to_n(lower + (i * slope / 10), 4))
        # TODO: somehow only 8 parts are inserted Why? ^^^^^^^^
        print(str(fieldstepindex))
        print(str(fieldsteps[fieldstepindex]))
        loadM = "m.LoadFile(\"" + mfilename + "\")"
        writeScript(loadM, fieldstepindex)
        time.sleep(10)
    runHyteresis(nLoops, args)


def runHyteresis(n, args):
    success = False
    writeScriptLoop(n)
    time.sleep(10)
    mumaxoutput = subprocess.Popen(args)  # , shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(10)
    index = monitorTable(mumaxoutput)
    time.sleep(10)
    try:
        mumaxoutput.kill()
        mumaxoutput.wait()
    except:
        print("Could not stop mumax3, Is the process Running? ", sys.exc_info()[0])
    if index != 0:
        writeScript("", 0)
        adaptLoop(args)


def main(argv):
    global fieldsteps
    if len(argv) == 1:
        binary = os.path.basename(argv[0])
        print("Usage: {} [file] (mumax3args ...)".format(binary))
        sys.exit(1)
    # Check for a version of mumax3. The -version option doesnt exist yet but this prevents mumax from starting a local instance
    checkfor(['mumax3', '-version'])

    readFile(argv[-1])

    if len(argv) > 2:
        l = [['mumax3'], argv[1:]]
        args = [item for sublist in l for item in sublist]
    else:
        args = ["mumax3", scriptfileName]
    adaptLoop(args)
    print("Script finished ... OK!")


if __name__ == '__main__':
    main(sys.argv)
