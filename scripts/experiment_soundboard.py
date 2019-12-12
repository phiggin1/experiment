#!/usr/bin/env python

import time
import sys
import os
import rospy
import actionlib
import tf
import math
import numpy as np

from sound_play.libsoundplay import SoundClient
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from geometry_msgs.msg import PointStamped
from geometry_msgs.msg import Quaternion
from tf.transformations import quaternion_from_euler

DEBUG = True

'''
			"What is this [robot points at specific object]?",
			"Where is the _____?",
			"Can you describe and show me an object that is similarly sized?",
			"Could you place ___ next to _____?",
			"Can you tell me more about ______?",
			"What would you use this  [robot points at specific object] object for?",
			"How are ______ and ______ similar?",
			"How would you describe ________?",
			"How would you use ______?",
			"Can you describe one of the objects that you would use everyday?",
			"How is _______ different from _________?",
			"Could you sort all the objects by how useful you would find them?"
'''

def get_stamped_point(x,y,z):
	p = PointStamped()
	p.header.frame_id = "map"
	p.header.stamp = rospy.Time.now()
	p.point.x = x
	p.point.y = y
	p.point.z = z

	return p

def get_goal(theta):
	goal = MoveBaseGoal()
	q = quaternion_from_euler(0.0,  0.0, theta)
	goal.target_pose.header.frame_id = "map"
	goal.target_pose.header.stamp = rospy.Time.now()
	goal.target_pose.pose.position.x = 0.0
	goal.target_pose.pose.position.y = 0.0
	goal.target_pose.pose.position.z = 0.0
    	goal.target_pose.pose.orientation.x = q[0]
    	goal.target_pose.pose.orientation.y = q[1]
    	goal.target_pose.pose.orientation.z = q[2] 
    	goal.target_pose.pose.orientation.w = q[3]

	return goal

class SoundBoard:
	def __init__(self):
		self.questions = [
			["What is this", "?"],
			["Where is the ","."],
			["Can you describe this"," and show me an object that is similarly sized?"],
			["Could you place this"," next to that","."],
			["Can you tell me more about this","?"],
			["What would you use this object for","?"],
			["How are this ","and that similar","?"],
			["How would you describe this","?"],
			["How would you use this","?"],
			["Can you describe one of the objects that you would use everyday?"],
			["How is this "," different from that","?"],
			["Could you sort all the objects by how useful you would find them?"]
		]

		self.statements = [
			"yes",
			"no",
			"here"
		]

		self.objects = []
		f = open("/home/phiggins/objects.txt", 'r')
		for line in f:
			label,x,y,z = line.split(',')
			self.objects.append( (label, float(x), float(y) ,float(z)) )
		f.close()

		rospy.init_node('experiment', anonymous = True)

		self.voice = 'voice_kal_diphone'
		self.volume = 1.0
		self.soundhandle = SoundClient()
		self.client = actionlib.SimpleActionClient('move_base',MoveBaseAction)
		self.client.wait_for_server()
		self.point_publisher = rospy.Publisher('clicked_point', PointStamped, queue_size=10)
		self.tf_listener = tf.TransformListener()
		rospy.sleep(1)


	def prompt_questions(self):
		#os.system('clear') 
		for i,q in enumerate(self.questions):
			s = str(i)+": "
			for e in q:
				s += str(e)
			print(s)

	def prompt_objects(self):
		for i,o in enumerate(self.objects):
			s = str(i)+": "+o[0]
			print(s)

	def prompt_misc(self):
		#os.system('clear') 
		for i,s in enumerate(self.statements):
			print(i,": ",s)
	
	def print_question(self, question):
		s = ""
		for i, q in enumerate(question):
			if i < len(question)-1:
				s += q + "___________"
			else:
				s += q
		print(s)

	def high_level_prompt(self):
		print("0: Question")
		print("1: Statement")
		print("else: Quit")

	def run(self):
		a = 0		
		while True:
			#os.system('clear') 
			self.high_level_prompt()
			a = input()
			if a == 0:
				self.prompt_questions()
				q = input()
				if q >=0 and q < len(self.questions):
					self.print_question(self.questions[q])
					self.build_sentence(self.questions[q])
			elif a== 1:
				self.prompt_misc()
			else:
				break

	def build_sentence(self, question):
		num_references = len(question)-1

		objs = []
		for i in range(num_references):
			self.prompt_objects()
			o = input("Object:")

			if o >= 0 and o < len(self.objects):
				objs.append(self.objects[o])

		s = ""
		for i in range(num_references):
			print('Saying: %s' % question[i])
    			self.soundhandle.say(question[i], self.voice, self.volume)
			self.face_point(objs[i][1], objs[i][2], objs[i][3])
			self.publish_point(objs[i][1], objs[i][2], objs[i][3])
			i += 1


		#time.sleep(5)

	def face_point(self, x,y,z):
		#print("facing ",x,y,z)
		p = get_stamped_point(x,y,z)

		#wait for current transform to be published		
		self.tf_listener.waitForTransform("/map", "/base_link", rospy.Time.now(), rospy.Duration(5.0))
		#transform the point from whatever frame it came from to the pantil's frame
		base_pt = self.tf_listener.transformPoint("/base_link", p)

		px = base_pt.point.x
		py = base_pt.point.y

		d = math.sqrt(x*x+y*y)
		theta_sin = math.asin(py/d)
		theta_cos = math.acos(px/d)

		if theta_sin >= 0.0 and theta_cos >= 0:
			theta = theta_cos
		elif theta_sin >= 0.0 and theta_cos < 0:
			theta = theta_sin
		elif theta_sin < 0.0 and theta_cos >= 0:
			theta= theta_cos
		else:
			theta = -theta_cos

		

		goal = get_goal(theta)

		if DEBUG: print("sending goal", goal)
   		self.client.send_goal(goal)
		if DEBUG: print("waiting")
    		wait = self.client.wait_for_result()
    		if not wait:
        		rospy.logerr("Action server not available!")
        		rospy.signal_shutdown("Action server not available!")
		if DEBUG: print("done")

	def publish_point(self, x,y,z):
		p = get_stamped_point(x,y,z)

		#wait for current transform to be published		
		self.tf_listener.waitForTransform("/pantilt_link", "/map", rospy.Time.now(), rospy.Duration(4.0))
		#transform the point from whatever frame it came from to the pantil's frame
		pan_tilt_pt = self.tf_listener.transformPoint("/pantilt_link", p)

		self.point_publisher.publish(pan_tilt_pt)
		

if __name__ == '__main__':
	sb = SoundBoard()
	sb.run()



