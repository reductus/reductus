# -*- coding: latin-1 -*-
import numpy as np

def LoadUXDData(filename, path="", friendly_name=""):
    """ Load two-dimensional mesh scans from Bruker x-ray files """
    ###################
    # By André Guzmán #
    ###################

    #This program assumes that the step sizes of all Rocking Curves are the same
    #I do not know what will happen if they are not (I've never tried) - but the result will probably not be pretty

    ############# Variables #################################
    #Read from file header (applies to all ranges)
    wavelength = 0

    #Arrays
    data_array = [] #main array to return
    two_theta_array = [] #Isn't it good that I ended all these variables with _array - there's already a two_theta variable that it could've been mixed up with
    theta_array = [] #All of the tube angles for the various scans (Theta)
    counts_array = [] #Counts go here
    pixels_array = [] #This is all 1s
    monitor_array = [] #Does the *100 multiplication for detectorslit.in
    count_time_array = [] #Count times go here

    #Range variables
    #Range Constants (values that don't change within a range, but do change between ranges)
    curr_range = 0 #determines which range is being read
    prev_step_time = 0
    step_time = 0
    step_size = 0
    theta_start = 0
    two_theta = 0
    detector_slit = False
    #Range Counters (these change in the range - and most of them only count up)
    theta = 0
    range_counts_array = []
    range_theta_array = []
    ############# END Variables #################################

    file_obj = open(os.path.join(path, filename), 'r')
    np = numpy

    for lines in file_obj:
        line = lines.strip()

        if line != "" and line[0].isdigit():
            #add counts to the count array and other stuff
            range_theta_array.append(theta)
            theta += step_size
            range_counts_array.append(float(line))

        elif line.count("_WL1") != 0:
            nums = line.split(" = ")
            wavelength = float(nums[1].strip())
        elif line.count("; Data ") != 0:
            nums = line.split(" ")
            curr_range = int(nums[4].strip())
            #step_time = 0
            step_size = 0
            theta_start = 0
            two_theta = 0
            theta = 0

            if curr_range != 1:
                counts_array.append(range_counts_array)
                theta_array.append(range_theta_array)

                range_counts_array = []
                range_theta_array = []
        elif line.count("_STEPTIME") != 0:
            nums = line.split(" = ")
            step_time = float(nums[1].strip()) - prev_step_time #Step time increments for some reason, this fixes that
            prev_step_time = float(nums[1].strip())
            count_time_array.append(step_time)
        elif line.count("_STEPSIZE") != 0:
            nums = line.split(" = ")
            step_size = float(nums[1].strip())
        elif line.count("_START") != 0:
            nums = line.split(" = ")
            theta_start = float(nums[1].strip())
            theta = theta_start
        elif line.count("_2THETA") != 0:
            nums = line.split(" = ")
            two_theta = float(nums[1].strip())
            two_theta_array.append(two_theta)
        elif line.count("_DETECTORSLIT") != 0:
            nums = line.split(" = ")
            slit = nums[1].strip()

            if slit == "in":
                detector_slit = True
                monitor_array.append(1)
            else:
                detector_slit = False
                monitor_array.append(0.01)
        else:
            two = 1 + 1
            #This really doesn't need to be here (at all), but I like IF statements that end in ELSEs

    #For Loop skips over the last range (which might be important), so its added here
    if curr_range != 1:
        # Adding arrays to other arrays and resetting them
        counts_array.append(range_counts_array)
        theta_array.append(range_theta_array)

        range_counts_array = []
        range_theta_array = []

    #Now that we're done with reading the file, its time to set up the MetaArray
    file_obj.close() # We're done with the file now

    for i in range(curr_range):
        pixels_array.append(1)

    theta_range = theta_array[-1][-1] - theta_array[0][0]
    theta_elements = int(theta_range / step_size + 0.5) + 1 # Assumes the step sizes of all the ranges are the same

    data_array = np.zeros((theta_elements, curr_range, 4))
    data_theta_array = [] #Rhyming was totally intentional

    theta_incr = theta_array[0][0] # This is a bad name for this variable
    for i in range(theta_elements):
        data_theta_array.append(theta_incr)
        theta_incr += step_size

    for i in range(len(counts_array)):
        start = int((theta_array[i][0] - data_theta_array[0])/step_size + 0.5) #Add 0.5 for rounding - the int() function does strange things to floats
        stop = int(int(start + ((theta_array[i][-1] - theta_array[i][0])/step_size) + .5) + 1) #Add 1 because arrays that go from 0 to N have N+1 elements

        data_array[start:stop, i, 0] = counts_array[i]
        data_array[start:stop, i, 1] = pixels_array[i]
        data_array[start:stop, i, 2] = monitor_array[i]
        data_array[start:stop, i, 3] = count_time_array[i]

    info = [
        {"name": "theta", "units": "degrees", "values": data_theta_array},
        {"name": "twotheta", "units": "degrees", "values": two_theta_array}]
    info.append({"name": "Measurements", "cols": [
                        {"name": "counts"},
                        {"name": "pixels"},
                        {"name": "monitor"},
                        {"name": "count_time"}]})
    info.append({"filename": filename, "friendly_name": friendly_name, "path":path, "CreationStory": ""})

    data = MetaArray(data_array, dtype='float', info=info)
    return data

def LoadUXDMany(filedescriptors):
    result = []
    for fd in filedescriptors:
        new_data = LoadUXDData(fd['filename'], friendly_name=fd['friendly_name'])
        if isinstance(new_data, list):
            result.extend(new_data)
        else:
            result.append(new_data)
    return result
