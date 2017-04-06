#!/usr/bin/env python
from __future__ import print_function
import roslib
roslib.load_manifest('lane_detection')
import rospy
import sys
from std_msgs.msg import String
from std_msgs.msg import Int32
from std_msgs.msg import Float64
import cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from picamera import PiCamera
from picamera.array import PiRGBArray
import time
import numpy as np
import RPi.GPIO as GPIO

last_error = 0
I = 0

def calculatePD(error, Kp, Kd, Ki):
	global last_error
	global I
#	I = 0
	P = error
	if P > 100:
		P = 100
	elif P < -100:
		P = -100

	I = I + error
	if I > 500:
		I = 500
	elif I < -500:
		I = -500
#	if (last_error > 0 and error < 0) or (last_error < 0 and error > 0):
#		I = 0

	D = error - last_error
	PID = Kp*P + Ki*I + Kd*D
#	PD = Kp*P + Kd*D
	last_error = error
	return PID
#	return PD

#def PID(P,I,D,Integrator_max,Integrator_min, set_point, current_value):
 #       # PID Controller
  #      Kp = P
##        Ki = I
  ##      Kd = D
#
#	Integrator = 0.0
#	Derivator = 0.0
#
 #       error = set_point - current_value
  #     	P = Kp * error
   #    	D = Kd * (error-Derivator)
    #   	Integrator = Integrator + error
#
#	if Integrator > Integrator_max:
#		Integrator = Integrator_max
#	elif Integrator < Integrator_min:
#		Integrator = Integrator_min
#
 #       I = Integrator + Ki
#
 #      	PID = P + I + D
#	return PID

def detect(img):
	# Gaussian Filter to remove noise
	img = cv2.medianBlur(img,5)
	gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

	# print img.shape = (200,350,3)
	rows,cols,channels = img.shape
	
	# ROI
	roi_mask = np.zeros(img.shape,dtype=np.uint8)
	roi_mask[10:rows,0:cols] = 255
	street = cv2.bitwise_and(img,roi_mask)

	stop_roi_mask = np.zeros(gray.shape,dtype=np.uint8)
	stop_roi_mask[100:rows,150:250] = 255

	first_right_roi_mask = np.zeros(gray.shape,dtype=np.uint8)
	first_right_roi_mask[rows/3:rows,220:360] = 255

	first_left_roi_mask = np.zeros(gray.shape,dtype=np.uint8)
	first_left_roi_mask[rows/3:rows,0:180] = 255

        second_right_roi_mask = np.zeros(gray.shape,dtype=np.uint8)
        second_right_roi_mask[rows/4:rows,220:360] = 255

        second_left_roi_mask = np.zeros(gray.shape,dtype=np.uint8)
        second_left_roi_mask[rows/4:rows,0:180] = 255

	# define range of color in HSV
	hsv = cv2.cvtColor(street,cv2.COLOR_BGR2HSV)

	sensitivity = 60 # range of sensitivity=[90,150]
	lower_white = np.array([0,0,255-sensitivity])
	upper_white = np.array([255,sensitivity,255])

	white_mask = cv2.inRange(hsv,lower_white,upper_white)
	white_mask = cv2.erode(white_mask, None, iterations=2)
	white_mask = cv2.dilate(white_mask, None, iterations=2)
	
	lower_red = np.array([0,240,200])
	upper_red = np.array([0,255,200])

	red_mask = cv2.inRange(hsv,lower_red,upper_red)
	red_mask = cv2.erode(red_mask, None, iterations=2)
	red_mask = cv2.dilate(red_mask, None, iterations=2)

	lower_yellow = np.array([5,0,0]) #0,100,100
	upper_yellow = np.array([50,255,255]) #80,255,255

	yellow_mask = cv2.inRange(hsv,lower_yellow,upper_yellow)
	yellow_mask = cv2.erode(yellow_mask, None, iterations=2)
	yellow_mask = cv2.dilate(yellow_mask, None, iterations=2)

	# mask AND original img
	whitehsvthresh = cv2.bitwise_and(street,street,mask=white_mask)
	yellowhsvthresh = cv2.bitwise_and(street,street,mask=yellow_mask)
	redhsvthresh = cv2.bitwise_and(street,street,mask=red_mask)

	# Canny Edge Detection 
	right_edges = cv2.Canny(whitehsvthresh,100,200)
	left_edges = cv2.Canny(yellowhsvthresh,100,200)

	first_right_edges = cv2.bitwise_and(right_edges,first_right_roi_mask)
	first_left_edges = cv2.bitwise_and(left_edges,first_left_roi_mask)

#        second_right_edges = cv2.bitwise_and(right_edges,second_right_roi_mask)
#        second_left_edges = cv2.bitwise_and(left_edges,second_left_roi_mask)

	red_edges = cv2.Canny(redhsvthresh,100,200)
	red_edges = cv2.bitwise_and(red_edges,stop_roi_mask)
	
	# Probabilistic Hough Transform
#	minLength=50
#	maxGap=10
#	right_lines = cv2.HoughLinesP(right_edges,1,np.pi/180,30,minLength,maxGap)
#	left_lines = cv2.HoughLinesP(left_edges,1,np.pi/180,30,minLength,maxGap)
#	red_lines = cv2.HoughLinesP(red_edges,1,np.pi/180,100,minLength,maxGap)
#
#	w = 205 # da controllare
#	lw = 20 # da controllare
#	ly = 15 # da controllare
#	i = 0
#	j = 0
#	d = []
#	phi = []
#	if right_lines is not None:
#		for x in range(0,len(right_lines)):
#			for x1,y1,x2,y2 in right_lines[x]:
#				d_i = ((x1+x2)/2)-(w/2)
#				if x2>x1:
#					d_i = d_i - lw
#				d.insert(i,d_i)
#				a = x2-x1
#				if x2<x1:
#					a = -a
#				phi.insert(j,(np.pi)/2 - np.arctan(a/(y2-y1)))
#				i+1
#				j+1
#				rospy.loginfo("Right lane: ")
#				rospy.loginfo(d)
#				
#	if left_lines is not None:
#		for x in range(0,len(left_lines)):
#			for x1,y1,x2,y2 in left_lines[x]:	
#				d_i = ((x1+x2)/2)+(w/2)
#				if x2>x1:
#					d_i = d_i + ly
#				d.insert(i,d_i)
#				a = x2-x1
#				if x2<x1:
#					a = -a
#				phi.insert(j,(np.pi)/2) - np.arctan2((x2-x1)/(y2-y1))
#				i+1
#				j+1
#				rospy.loginfo("Left lane: ")
#				rospy.loginfo(d)
##	rospy.loginfo(d)
##	rospy.loginfo(phi)
#
##	bufferx_right = []
##	i=0
##	j=0
##	mdx=[]
 ##       if lines_right is not None:
  ##              for x in range(0,len(lines_right)):
   ##                    for x1,y1,x2,y2 in lines_right[x]:
    ##                            if x2!=x1:
 ##	                                m=(y2-y1)/(float(x2-x1))
  ##      	                        #alpha=np.arctan(m)
##				mdx.insert(j,m)
 ##               	        bufferx_right.insert(i,x1)
  ##                      	i+1
   ##                             bufferx_right.insert(i,x2)
    ##                            i+1
##				j+1
##	bufferx_left = []
##	i=0
##	j=0
##	msx=[]
 ##       if lines_left is not None:
  ##              for x in range(0,len(lines_left)):
   ##                    for x1,y1,x2,y2 in lines_left[x]:
    ##                            if x2!=x1:
     ##                                   m=(y2-y1)/(float(x2-x1))
      ##                                  #alpha=np.arctan(m)
       ##                         msx.insert(j,m)
	##			bufferx_left.insert(i,x1)
         ##                       i+1
          ##                      bufferx_left.insert(i,x2)
           ##                     i+1
	##			j+1
##        x=0
 ##       mx_right=0
  ##      for j in range(0,len(bufferx_right)):
   ##             x+=bufferx_right[j]
##	if len(bufferx_right)!=0:
##	        mx_right=x/len(bufferx_right)
##
##	x=0
##	mx_left=0
##	for k in range(0,len(bufferx_left)):
##		x+=bufferx_left[k]
##	if len(bufferx_left)!=0:
##		mx_left=x/len(bufferx_left)
##
##	mx=(mx_right+mx_left)/2
##
##	x=0
##	m_right = 0
##	for j in range(0,len(mdx)):
##		x+=mdx[j]
##	if len(mdx)!=0:
##		m_right=x/len(mdx)
##
##	x=0
##	m_left=0
###	for k in range(0,len(msx)):
###		x+=msx[k]
#	if len(msx)!=0:
#		m_left=x/(len(msx))
#
#	m = (m_right+m_left)/2	
#		
#	if lines_right is not None and lines_left is not None:
#		if (mx<=250 and mx>=150):
#			return "forward"
#		elif mx>250:
#			return "left"
#		elif mx<150:
#			return "right"
#	elif lines_left is None and lines_right is not None:
#		if mdx>0.8:
#			return "forward"
#		else:
#			return "left"
#	elif lines_right is None and bufferx_left is not None:
#		if msx>0.8:
#			return "forward"
#		else:
#			return "right"
#	else:
#		return "x"

	# Standard Hough Transform
	right_lines = cv2.HoughLines(first_right_edges,0.8,np.pi/180,40)
	left_lines = cv2.HoughLines(first_left_edges,0.8,np.pi/180,35)
	red_lines = cv2.HoughLines(red_edges,1,np.pi/180,40)
	
#	second_right_lines = cv2.HoughLines(second_right_edges,1,np.pi/180,30)
#        second_left_lines = cv2.HoughLines(second_left_edges,1,np.pi/180,30)

#	if right_lines is None or left_lines is None:
#		right_lines = second_right_lines
#		left_lines = second_left_lines
#		rospy.loginfo("Seconda ROI")
#	else:
#		rospy.loginfo("Prima ROI")

	xm = cols/2
	ym = rows
	
	# Draw right lane
	x_1 = []
	x_2 = []
	x_3 = []
	i = 0
	if right_lines is not None:
		right_lines = np.array(right_lines[0])
		for rho, theta in right_lines:
                        a=np.cos(theta)
                        b=np.sin(theta)
                        x0,y0=a*rho,b*rho
#                       pt1=(int(x0+1000*(-b)),int(y0+1000*(a)))
#                       pt2=(int(x0-1000*(-b)),int(y0-1000*(a)))
#			cv2.line(img,pt1,pt2,(255,0,0),2)
                        y3 = 140
			x3 = int(x0+((y0-y3)*np.sin(theta)/np.cos(theta)))
			x_1.insert(i,x3)
			y4 = 100
			x4 = int(x0+((y0-y4)*np.sin(theta)/np.cos(theta)))
			x_2.insert(i,x4)
			y5 = 80
			x5 = int(x0+((y0-y5)*np.sin(theta)/np.cos(theta)))
			x_3.insert(i,x5)
			i+1

	if len(x_1) != 0:
		xmin = x_1[0]
		for k in range(0,len(x_1)):
			if x_1[k] < xmin and x_1[k] > 0:
				xmin = x_1[k]
		kr_1 = int(np.sqrt(((xmin-xm)*(xmin-xm))+((y3-ym)*(y3-ym))))
#		rospy.loginfo(xmin)
	else:
		kr_1 = 0
		xmin = 0
#	rospy.loginfo(kr_1)
#	rospy.loginfo(xmin)

        if len(x_2) != 0:
                xmin = x_1[0]
                for k in range(0,len(x_1)):
                        if x_2[k] < xmin:
                                xmin = x_2[k]
                kr_2 = int(np.sqrt(((xmin-xm)*(xmin-xm))+((y4-ym)*(y4-ym))))
        else:
                kr_2 = 0

        if len(x_3) != 0:
                xmin = x_3[0]
                for k in range(0,len(x_3)):
                        if x_3[k] < xmin:
                                xmin = x_3[k]
                kr_3 = int(np.sqrt(((xmin-xm)*(xmin-xm))+((y5-ym)*(y5-ym))))
        else:
                kr_3 = 0

	# Draw left lane
	x_1 = []
	x_2 = []
	x_3 = []
	turn = []
	i = 0
	if left_lines is not None:
		left_lines = np.array(left_lines[0])
		for rho, theta in left_lines:
                        a=np.cos(theta)
                        b=np.sin(theta)
                        x0,y0=a*rho,b*rho
                        pt1=(int(x0+1000*(-b)),int(y0+1000*(a)))
                        pt2=(int(x0-1000*(-b)),int(y0-1000*(a)))
			cv2.line(img,pt1,pt2,(0,255,0),2)
			y3 = 140
			x3 = int(x0+((y0-y3)*np.sin(theta)/np.cos(theta)))
			x_1.insert(i,x3)
			y4 = 100
			x4 = int(x0+((y0-y4)*np.sin(theta)/np.cos(theta)))
			x_2.insert(i,x4)
			y5 = 80
			x5 = int(x0+((y0-y5)*np.sin(theta)/np.cos(theta)))
			x_3.insert(i,x5)
			y_turn = 155
			x_turn = int(x0+((y0-y_turn)*np.sin(theta)/np.cos(theta)))
			turn.insert(i,x_turn)
			i+1

        if len(x_1) != 0:
                xmax = x_1[0]
                for k in range(0,len(x_1)):
                        if x_1[k] > xmax and x_1[k]<cols:# and x_1[k] > 0:
                                xmax = x_1[k]
                kl_1 = int(np.sqrt(((xmax-xm)*(xmax-xm))+((y3-ym)*(y3-ym))))
#		rospy.loginfo(xmax)
        else:
                kl_1 = 0
		xmax = 0
#	rospy.loginfo(kl_1)
#	rospy.loginfo(xmax)

        if len(turn) != 0:
                xmax = turn[0]
                for k in range(0,len(turn)):
                        if turn[k] > xmax:
                                xmax = turn[k]
                kl_turn = int(np.sqrt(((xmax-xm)*(xmax-xm))+((y3-ym)*(y3-ym))))
        else:
                kl_turn = 0

        if len(x_2) != 0:
                xmax = x_2[0]
                for k in range(0,len(x_2)):
                        if x_2[k] > xmax:
                                xmax = x_2[k]
                kl_2 = int(np.sqrt(((xmax-xm)*(xmax-xm))+((y4-ym)*(y4-ym))))
        else:
                kl_2 = 0
		xmax=0

        if len(x_3) != 0:
                xmax = x_3[0]
                for k in range(0,len(x_3)):
                        if x_3[k] > xmax:
                                xmax = x_3[k]
                kl_3 = int(np.sqrt(((xmax-xm)*(xmax-xm))+((y5-ym)*(y5-ym))))
        else:
                kl_3 = 0
		xmax = 0

	# Draw red lines
	if red_lines is not None:
		red_lines = np.array(red_lines[0])
		for rho, theta in red_lines:
			a=np.cos(theta)
                        b=np.sin(theta)
                        x0=a*rho
                        y0=b*rho
                        x1=int(x0+1000*(-b))
                        y1=int(y0+1000*(a))
                        x2=int(x0-1000*(-b))
                        y2=int(y0-1000*(a))

#	rospy.loginfo(kr_1)
#	rospy.loginfo(kl_1)
#	kl=0
#	kr=0
        kl = kl_1
        kr = kr_1

	error = kr - kl
        PID = (calculatePD(error,0.5,0,0.05))/1

	if red_lines is not None:
		rospy.loginfo("Stop")
		return 151 #stop
	elif right_lines is not None and left_lines is not None:
#		kr=0
#		kl=0
#		kl = kl_1
#		kr = kr_1
#	        elif kr_2 != 0 and kl_2 != 0:
#			kl = kl_2
#			kr = kr_2
#		elif kr_3 != 0 and kl_3 != 0:
#			kl = kl_3
#			kr = kr_3
#		error = kr - kl
#		rospy.loginfo(kr)
#		rospy.loginfo(kl)
        	rospy.loginfo(error)
#		PID = (calculatePD(error,30,0,0))/150
#		rospy.loginfo(I)
#		rospy.loginfo(PD)
#		rospy.loginfo(last_error)

		return PID
	elif left_lines is not None and right_lines is None:
		rospy.loginfo("Turn Right")
		rospy.loginfo(kl_1)
#		if kl_1 < 120:
		return 152 #turn right
#		else:
# 			return PID #forward
	elif left_lines is None and right_lines is not None:
		rospy.loginfo("Turn Left")
		return 153 #turn let
	elif left_lines is None and right_lines is None:
		rospy.loginfo("No line")
		return 155 #x
	else:
		return 155 #x
#	elif right_lines is None and left_lines is not None:
#		return 
#	rospy.loginfo(kl_turn)
#	error = kr - kl
#	PD = (calculatePD(error,2,0.5))/10

#	rospy.loginfo(error)
#	rospy.loginfo(PD)
#	
#	if red_lines is not None:
#		time.sleep(0.5)
#		return "stop"
#	if right_lines is not None and left_lines is not None:
#	if kr != 0 and kl != 0:
#		error = kr - kl
#		PD = (calculatePD(error,2,0.5))/10
#		rospy.loginfo(PD)
#		if PD > 10:
#			return "veldx+"
#		elif PD > 0:
#			return "veldx+"
#		elif PD < -10:
#			return "velsx+"
#		elif PD < 0:
#			return "velsx+"
#		else:
#			return "forward"

#	elif right_lines is not None and left_lines is None:
#		if kr_2 > 50:
#			return "forward"
#		else:
#			return "turn_left"
#	elif right_lines is None and left_lines is not None:
##		if kl_turn > 150:
##			return "forward"
##		else:
##		time.sleep(1)
#		return "turn_right"
#	elif right_lines is None and left_lines is None:
#		return "end"

#	rospy.loginfo(error)
#	rospy.loginfo(last_error)
#	rospy.loginfo(PID)
#	if red_lines is not None:
#		time.sleep(0.1)
#		return "stop"
##		time.sleep(2)
#	if kr == 0 and kl == 0:
#		return "x"
##	elif pid == 0:
##		return "forward"
#	elif kr != 0 and kl != 0:
#		if PID > 50:
#			return "right"
#		elif PID < -50:
#			return "left"
#		else:
#			return "forward"
#	elif kr > 0 and kr < 300 and kl == 0:
#		if kr>100:
#			return "forward"
#		else:
#			return "left"
#	elif kl > 0 and kl < 300 and kr == 0:
#		if kl>100:
#			return "forward"
#		else:
#			return "right"
#	else:	
#		return "forward"

#	if kl!=0 and kr!=0:
#		rospy.loginfo(pid)

#	Kp = 10
#	Kd = 1
#	Ki = 0
#
#	last_P = 0
#	I=0
#	D=0
##	P = kr-kl
#	D = P - last_P
#	I = I + P
##	last_P = P
#	PID = Kp*P + Kd*D + Ki*I
#	rospy.loginfo(PID)	

	# Draw STOP line
#	if red_lines is not None:
#		red_lines = np.array(red_lines[0])
#		for rho, theta in red_lines:
 #                       a=np.cos(theta)
  #                      b=np.sin(theta)
   #                     x0,y0=a*rho,b*rho
    #                    pt1=(int(x0+1000*(-b)),int(y0+1000*(a)))
     #                   pt2=(int(x0-1000*(-b)),int(y0-1000*(a)))
#	
#	if (kr != 0 and kl != 0 and red_lines is None):
#		if (kr-kl < 50 and kr-kl > 0) or (kl-kr < 50 and kl-kr > 0):
#		if (kr == kl):
#			return "forward" # Go straight
#		elif kl > kr:
#			return "left" # Turn left
#		elif kr > kl:
#			return "right" # Turn right
#	elif (kr > 0 and kr < 300 and kl == 0 and red_lines is None):
##		if kr > 40:
##			return "forward"
##		else:
#		return "left" # Turn left
#	elif (kr == 0 and kl > 0 and kl < 300 and red_lines is None):
##		if kl > 40:
##			return "forward"
##		else:
#		return "right" # Turn right
#	elif red_lines is not None:
#		time.sleep(1)
#		return "stop" # STOP
#	else:
#		return "x" # No lane found

###### Vecchio algoritmo: ########
	
#	if red_lines is not None:
#		time.sleep(0.5)
#		return "stop" # STOP
#
#	if right_lines is not None:
#		if left_lines is not None:
#			return "f" # Go straight
#		elif left_lines is None:
#			return "l" # Turn left
#	elif right_lines is None:
#		if left_lines is not None:
#			return "r" # Turn right
#		elif left_lines is None:
#			return "x" # No line found
#
#	return "x"

def talker():
	pub = rospy.Publisher('lane_detection', Int32, queue_size=10)
	rospy.init_node('talker',anonymous=True)

	camera = PiCamera() # Raspberry Pi Camera
	camera.resolution = (350,200)
	camera.framerate = 50
	camera.contrast = 40 #30
	camera.saturation = 100 #20
	camera.brightness = 30 #40
	camera.sharpness = 0
	camera.start_preview()
	time.sleep(1)
	rawCapture = PiRGBArray(camera)
	
	rate = rospy.Rate(30) # publisher frequency
	bridge = CvBridge()

	while not rospy.is_shutdown():
		camera.capture(rawCapture, format='bgr', use_video_port=True)
		rospy.loginfo("Sending an Image Message")
		info = detect(rawCapture.array)
		pub.publish(info)
		rawCapture.truncate(0)
#		rate.sleep()

if __name__ == '__main__':
	try:
		talker()
	except rospy.ROSInterruptException:
		pass
