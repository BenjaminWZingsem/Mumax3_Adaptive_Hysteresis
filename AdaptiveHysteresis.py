import csv
import math
import os
import os.path
import re
import shutil
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
forkTypeSimulation = False
ForkStep = 0.0
Sampling = 2


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
    global forkTypeSimulation
    global ForkStep
    global Sampling

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

    pattern = re.compile("FORKtype.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        forkTypeSimulationtmp = int(match.group().split("=")[1].split(";")[0])
        if forkTypeSimulationtmp == 0:
            forkTypeSimulation = False
        else:
            forkTypeSimulation = True

    if forkTypeSimulation:
        pattern = re.compile("ForkStep.*\\=.*-*;")
        match = pattern.search(instructions)
        if match:
            ForkStep = float(match.group().split("=")[1].split(";")[0])

    pattern = re.compile("Sampling.*\\=.*-*;")
    match = pattern.search(instructions)
    if match:
        Sampling = float(match.group().split("=")[1].split(";")[0])
        if Sampling < 2:
            Sampling = 2
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
    continueEvaluation = True
    index = 0
    while True:
        try:
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
            for i in range(0, len(magne)):
                m = magne[i]
                b = field[i]
                # print(norm(minus(btmp, b)))
                if (abs(dot3D(minus(mtmp, m), eB())) < MmaxDiff) | (round_to_n(norm(minus(btmp, b)), 9) <= BminStep):
                    # print("Step: " + str(round_to_n(norm(minus(btmp, b)), 3)) + ", " + str(
                    #    norm(minus(btmp, b))) + "Minstep: " + str(BminStep))o
                    mtmp = m
                    btmp = b
                else:
                    print("Step: " + str(round_to_n(norm(minus(btmp, b)), 4)) + ", (" + str(
                        norm(minus(btmp, b))) + ") Minstep: " + str(BminStep))
                    print("fail: FIELD_STEP TOO LARGE BETWEEN M = " + str(mtmp) + " AND M = " + str(m))
                    print("fail: FIELD_STEP TOO LARGE BETWEEN B = " + str(btmp) + " AND B = " + str(b))
                    print("Delta_M = " + str(abs(dot3D(minus(mtmp, m), eB()))) + ", Delta_B = " + str(
                        round_to_n(norm(minus(btmp, b)), 4)))
                    print("a = (abs(dot3D(minus(mtmp, m), eB())) < MmaxDiff) = " + str(
                        (abs(dot3D(minus(mtmp, m), eB())) < MmaxDiff)))
                    print("b = (round_to_n(norm(minus(btmp, b)), 3) <= BminStep) = " + str(
                        (round_to_n(norm(minus(btmp, b)), 4) <= BminStep)))
                    print("a|b = " + str((abs(dot3D(minus(mtmp, m), eB())) < MmaxDiff) | (
                        round_to_n(norm(minus(btmp, b)), 4) <= BminStep)))
                    index = i
                    return index
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
        if not (mumaxoutput.poll() is None):
            # TODO: Handle returncode accordingly
            if continueEvaluation == False:
                print("Returning index: " + str(index))
                break
            continueEvaluation = False
            # wait for Filesystem to finish writing table, then monitor table once more. If it doenst fail, then break
            # loop and return 0
            time.sleep(10)
    return index


def checkfor(args):
    """Make sure that a mumax3 is available in PATH

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
    try:
        # Delete OutputFolder and all m*.ovf files.
        # Not deleting the outputfolder first seems to cause mumax to throw weird "set mesh first" error
        shutil.rmtree(os.getcwd() + "/" + (".".join(scriptfileName.split(".")[0:-1])) + ".out")
    except:
        print("Could not delete \'.out\' Folder. Is this the first iteration?", sys.exc_info())
    index = 1
    fieldstepindex = 0
    while index != 0:
        time.sleep(1)
        restart = True
        while restart:
            mumaxoutput = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(5)
            restart = ((not (mumaxoutput.poll() is None)) | (mumaxoutput.poll() == 0))
            print(mumaxoutput.poll())

        index = monitorTable(mumaxoutput)
        if index == 0:
            break
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
        dest = os.getcwd()  # os.path.dirname(__file__)
        # print("SRC: " + str(src))
        # print("DEST: " + str(dest))
        copy2(src, dest)
        time.sleep(10)
        mumaxoutput.kill()
        mumaxoutput.wait()

        upper = fieldsteps[fieldstepindex + 1]
        lower = fieldsteps[fieldstepindex]
        slope = upper - lower
        print("FIELD_STEP TOO LARGE BETWEEN " + str(lower) + " AND " + str(upper))
        print(fieldsteps)
        for i in range(1, Sampling):
            fieldsteps.insert(fieldstepindex + (i), round_to_n(lower + (i * slope / Sampling), 9))
        print(str(fieldstepindex))
        print(str(fieldsteps[fieldstepindex]))
        print(fieldsteps)
        loadM = "m.LoadFile(\"" + mfilename + "\")"
        writeScript(loadM, fieldstepindex)
        time.sleep(10)
    runHyteresis(nLoops, args)


def runHyteresis(n, args):
    print("Starting actual Hysteresis. Cross your fingers!")
    try:
        # Delete OutputFolder and all m*.ovf files.
        # Not deleting the outputfolder first seems to cause mumax to throw weird "set mesh first" error
        shutil.rmtree(os.getcwd() + "/" + (".".join(scriptfileName.split(".")[0:-1])) + ".out")
    except:
        print("Could not delete \'.out\' Folder. What have you done?", sys.exc_info()[0])
    fieldstepindex = 0
    writeScriptLoop(n)

    time.sleep(1)
    restart = True
    while restart:
        mumaxoutput = subprocess.Popen(args)  # , shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)
        restart = ((not (mumaxoutput.poll() is None)) | (mumaxoutput.poll() == 0))
        print(mumaxoutput.poll())

    index = monitorTable(mumaxoutput)
    time.sleep(10)
    try:
        mumaxoutput.kill()
        mumaxoutput.wait()
    except:
        print("Could not stop mumax3, Is the process Running? ", sys.exc_info()[0])

    print("INDEX = " + str(index))
    #TODO: Move this code into a function, such that it can be accessed by hysteresis and adaptation
    if index != 0:
        # TODO: If saveM simulation can pick up at last known m*.ovf just like adaptation
        fieldstepindex = fieldstepindex + index - 1
        upper = fieldsteps[fieldstepindex + 1]
        lower = fieldsteps[fieldstepindex]
        slope = upper - lower
        print("Decreasing FIELD_STEP between |B| = " + str(lower) + " AND |B| = " + str(upper))
        # TODO: Binary enusres no oversampling, but requires alot of restarts
        # TODO: it must be somehow possible to pause the script and continue, just like in the web interface
        for i in range(1, Sampling):
            fieldsteps.insert(fieldstepindex + (i), round_to_n(lower + (i * slope / Sampling), 9))
        writeScript("", 0)
        adaptLoop(args)


def main(argv):
    global fieldsteps
    if len(argv) == 1:
        binary = os.path.basename(argv[0])
        print("Usage: {} [file] (mumax3args ...)".format(binary))
        sys.exit(1)
    # Check for a version of mumax3. The -version option doesnt exist yet but this prevents mumax from starting a local
    # instance
    checkfor(['mumax3', '-version'])
    print(os.getcwd())
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
