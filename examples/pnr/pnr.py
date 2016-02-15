"""
pnr.py: GUIDED mode to "Point of No Return" example (Copter Only)
Demonstrates arming, takeoff and fly away.  When the battery and distence from "home" 
reach the Point of No Return the Copter mode is set to "RTL". 
Full documentation is provided at http://python.dronekit.io/examples/pnr.html

NOTE - To run this you will need to install the apscheduler
   sudo pip install apscheduler

"""

from dronekit import connect, VehicleMode, LocationGlobalRelative
from apscheduler.schedulers.background import BackgroundScheduler  # note that there are many other schedulers available
from geopy.distance import vincenty
import argparse  
import time
import math

import logging
logging.basicConfig()

calc_rate = 2.0
route_time = 240
lat1 = 0.0
lon1 = 0.0

"""
Point of No Return Calculation.
http://www.airsafaris.com.au/general_info/pnrcp.htm
"""
pnr_counter = 0.0
pnr_reached = 0
groundspeed_cumulation = 0.0
def point_of_no_return():
    global pnr_reached
    global pnr_counter
    global lat1
    global lon1
    global groundspeed_cumulation

    pnr_counter = pnr_counter + 1

    print "----- PNR=%s" % pnr_reached
    print "  Calulating PNR #%s" % pnr_counter

    time_in_flight = pnr_counter * calc_rate
    print "  Time in flight %3.4f" % time_in_flight

    print "  Current Bat %3f" % (vehicle.battery.level - 5.0)  # safe 5% of batter in reserve
    battery_drop_rate = (100.0 - vehicle.battery.level) / time_in_flight 
    print "  Battery usage is %3.4f" % battery_drop_rate

    lat2 = vehicle.location.global_relative_frame.lat
    lon2 = vehicle.location.global_relative_frame.lon
    location2 = (lat2, lon2)
    d = vincenty(location1, location2).meters
    print "  Distance to home %3.4f" % d

    if battery_drop_rate == 0:
        battery_drop_rate = 1
    remaining_flight_time = vehicle.battery.level / battery_drop_rate  # remaining flight time in seconds
    print "  Remaining flight time %3.4f" % remaining_flight_time

    return_home_time = d / 5.0  # return to launch is set to 5.0 mps
    print "  Return home time %3.4f" % return_home_time

    pnr = (remaining_flight_time - return_home_time)
    print "  Flight time before PNR %3.4f" % pnr

    if pnr < 60.0 and pnr_reached != 1 :
        print "PNR - Returning to Launch"
        pnr_reached = 1
        vehicle.mode    = VehicleMode("RTL")

    return


#Set up option parsing to get connection string
parser = argparse.ArgumentParser(description='Print out vehicle state information. Connects to SITL on local PC by default.')
parser.add_argument('--connect', default='127.0.0.1:14550',
                   help="vehicle connection target. Default '127.0.0.1:14550'")

args = parser.parse_args()


# Connect to the Vehicle
print 'Connecting to vehicle on: %s' % args.connect
vehicle = connect(args.connect, wait_ready=True)


def arm_and_takeoff(aTargetAltitude):
    """
    Arms vehicle and fly to aTargetAltitude.
    """

    print "Basic pre-arm checks"
    # Don't try to arm until autopilot is ready
    while not vehicle.is_armable:
        print " Waiting for vehicle to initialise..."
        time.sleep(1)

        
    print "Arming motors"
    # Copter should arm in GUIDED mode
    vehicle.mode    = VehicleMode("GUIDED")
    vehicle.armed   = True    

    # Check if we have reached the Point of No Rerturn ever 10 seconds
    print "Starting PNR calculation"
    sched = BackgroundScheduler()
    sched.add_job(point_of_no_return, 'interval', seconds = calc_rate)
    sched.start()

    # Confirm vehicle armed before attempting to take off
    while not vehicle.armed:      
        print " Waiting for arming..."
        time.sleep(1)

    print "Taking off!"
    vehicle.simple_takeoff(aTargetAltitude) # Take off to target altitude

    # Wait until the vehicle reaches a safe height before processing the goto (otherwise the command 
    #  after Vehicle.simple_takeoff will execute immediately).
    while True:
        print " Altitude: ", vehicle.location.global_relative_frame.alt 
        #Break and return from function just below target altitude.        
        if vehicle.location.global_relative_frame.alt>=aTargetAltitude*0.95: 
            print "Reached target altitude"
            break
        time.sleep(1)
    return
#
# Start mission
#
# Record our Launch location
lat1 = vehicle.location.global_relative_frame.lat
lon1 = vehicle.location.global_relative_frame.lon
location1 = (lat1,lon1)

arm_and_takeoff(10)

print "Set default/target airspeed to 3"
vehicle.airspeed=3

print "Going towards first point for %s seconds ..." % route_time
point1 = LocationGlobalRelative(35.567081, -97.599866, 20)
vehicle.simple_goto(point1)
vehicle.simple_goto(point1, groundspeed=30)

# sleep so we can see the change in map
time.sleep(route_time)


if not pnr_reached:
    print "Going towards second point for %s seconds (groundspeed set to 10 m/s) ..." % route_time
    point2 = LocationGlobalRelative(45.570819, -97.578888, 20)
    vehicle.simple_goto(point2, groundspeed=20)

# sleep so we can see the change in map
time.sleep(route_time)

if not pnr_reached:
    print "Going towards launch point for %s seconds (groundspeed set to 30 m/s) ..." % route_time
    point2 = LocationGlobalRelative(lat1, lon1, 20)
    vehicle.simple_goto(point2, groundspeed=30)

# sleep so we can see the change in map
time.sleep(route_time)

if not pnr_reached:
    print "Returning to Launch"
    vehicle.mode = VehicleMode("RTL")

sched.shutdown(wait=False)

#Close vehicle object before exiting script
print "Close vehicle object"
vehicle.close()

