
import matplotlib.pyplot as plt
from math import *
import numpy as np
import random
import time
from map import *
from ekfslam import *
plt.ion()


class Robot:
    # simulate a robot model that can sense landmarks and move
    # state is represented in form of (x(m),y(m),theta(rad))
    # control is given by (linear_vel(m/s), ang_vel(rad/s), time_var(s))
    # the sensor are able to locate landmarks in a range given by the "sensor_maxrange"
    # and "sensor_opening"

    # init:
    #    creates robot and initializes location/orientation
    def __init__(self,init_state,map):
        self.USE_NOISE = True
        self.USE_KALMAN = True
        self.map = map
        self.state = [0.0,0.0,0.0] #state is the REAL place occupy by the robot
        self.states_list = [init_state] #store all visited states
        self.sensor_maxrange = 5.0
        self.sensor_opening =  3*pi/2.0
        self.visible_landmarks = []  #current visible landmarks
        self.measure_noise = 0.00
        self.control_noise = [0.1,-0.2,0]
        self.odometry = [0.0,0.0,0.0]
        self.odometry_list = []
        self.ekf = ExtendedKalmanFilterSLAM(self.state)

    # set_state:
    #       set the robot to a desired state
    def set_state(self,state):
        #set state
        self.state = state

    #apply_control_noise
    #   apply a sistematic and a random noise given in self.control_noise
    #   return: control with noise
    def apply_control_noise(self, control):

        rand = np.random.rand(2)
        rand[0]*= 0.03*control[0]
        rand[1]*= 0.03*control[1]

        v = control[0] + self.control_noise[0]*control[0] + rand[0]
        w = control[1] + self.control_noise[1]*control[1] + rand[1]
        return [v,w,control[2]]

    # move
    #       execute a control instructios in the form of (v,w,dt)
    def move(self,control):

        #member variable of control with error
        if(self.USE_NOISE):
            [v,w,dt] = self.apply_control_noise(control)
        else:
            [v,w,dt] = control

        #member variables for state
        x = self.state[0]
        y = self.state[1]
        theta = self.state[2]

        if w == 0:
            new_x = x + cos(theta) * dt
            new_y = y + sin(theta) * dt
            new_theta = theta
        else:
            new_x = x - (v/w)*sin(theta) + (v/w) * sin(theta + (w*dt))
            new_y = y + (v/w)*cos(theta) - (v/w) * cos(theta + (w*dt))
            new_theta = (theta + w*dt) % (2*pi)

        #update state and append it to states list
        self.state =[float("{0:.4f}".format(new_x)),
                    float("{0:.4f}".format(new_y)),
                    float("{0:.4f}".format(new_theta))]

        self.states_list.append(self.state)

        self.search_landmarks(self.map.global_landmark_list)

        self.update_odometry([control[0],control[1],dt])


    #update_odometry
    #   updates current guess of robot pose given control command
    def update_odometry(self,control):
        if self.USE_KALMAN:
            self.ekf.predict(control)
            for landmark in self.visible_landmarks:
                #convert global coordinates to measurements
                dx = landmark[0] - self.state[0]
                dy = landmark[1] - self.state[1]
                alpha = (atan2(dy, dx) - self.state[2] + pi) % (2*pi) - pi
                r = sqrt(dx * dx + dy * dy)

                #associate current landmark measure with previus landmarks
                x,y,theta = self.ekf.state[:3]
                idx = self.ekf.associate_landmark(landmark)

                # if there is no correspondence, add new landmark
                if idx == -1:
                    idx = self.ekf.add_landmark_to_state(landmark)

                # correct the estimate state with the observed landmark
                self.ekf.correct([r,alpha],idx)

            #update odometry
            self.odometry = self.ekf.state
            self.odometry_list.append(self.odometry)

        else:
            self.ekf.predict(control)
            self.odometry = self.ekf.state
            self.odometry_list.append(self.odometry)


    #apply_measurement_noise
    #   apply a sistematic and a random noise given in self.measure_noise
    #   return: ladmark with noise
    def apply_measurement_noise(self, landmark_coord):

        return [landmark_coord[0],landmark_coord[1]]


    #is_landmark_visible
    #   check if a landmarks is visible to the sensor given the min/max angle
    #   and the max range.
    #   returns True or False
    def is_landmark_visible(self,landmark):
        dx = landmark[0] - self.state[0]
        dy = landmark[1] - self.state[1]

        alpha = (atan2(dy, dx) - self.state[2] + pi) % (2*pi) - pi
        r = sqrt(dx * dx + dy * dy)
        min_b = -3*pi/4.0
        max_b = 3*pi/4.0

        if alpha >= min_b and alpha <= max_b and r < self.sensor_maxrange:
            return True
        else: return False


    #search_landmarks
    #   given the coordinates of all the landmarks in the system, updates the
    #   self.landmark_list with the visible ones
    def search_landmarks(self,global_landmark_list):
        landmarks = []
        #verifica os landmarks visiveis no mapa
        for landmark in global_landmark_list:
            if(self.is_landmark_visible(landmark)):
                landmarks.append(self.apply_measurement_noise(landmark))
        self.visible_landmarks = landmarks



    #__repr__
    #   allows printing the robot state using print function
    def __repr__(self):
        return '[x=%s y=%s theta=%s]' % (str(self.state[0]), str(self.state[1]),
                                                str(self.state[2]))
