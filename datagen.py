# -*- coding: utf-8 -*-
"""
Deep Human Pose Estimation
 
Project by Walid Benbihi
MSc Individual Project
Imperial College
Created on Wed Jul 12 15:53:44 2017
 
@author: Walid Benbihi
@mail : w.benbihi(at)gmail.com
@github : https://github.com/wbenbihi/hourglasstensorlfow/
 
Abstract:
        This python code creates a Stacked Hourglass Model
        (Credits : A.Newell et al.)
        (Paper : https://arxiv.org/abs/1603.06937)
        
        Code translated from 'anewell' github
        Torch7(LUA) --> TensorFlow(PYTHON)
        (Code : https://github.com/anewell/pose-hg-train)
        
        Modification are made and explained in the report
        Goal : Achieve Real Time detection (Webcam)
        ----- Modifications made to obtain faster results (trade off speed/accuracy)
        
        This work is free of use, please cite the author if you use it!

"""
import numpy as np
import cv2
import os
import matplotlib.pyplot as plt
import random
import time
from skimage import transform
import scipy.misc as scm
import copy

class DataGenerator():
	""" DataGenerator Class : To generate Train, Validation and Test sets
	for the Deep Human Pose Estimation Model 
	Formalized DATA:
		Inputs:
			Inputs have a shape of (Number of Image) X (Height: 256) X (Width: 256) X (Channels: 3)
		Outputs:
			Outputs have a shape of (Number of Image) X (Number of Stacks) X (Heigth: 64) X (Width: 64) X (OutputDimendion: 16)
	Joints:
		We use the MPII convention on joints numbering
		List of joints:
			00 - Right Ankle
			01 - Right Knee
			02 - Right Hip
			03 - Left Hip
			04 - Left Knee
			05 - Left Ankle
			06 - Pelvis (Not present in other dataset ex : LSP)
			07 - Thorax (Not present in other dataset ex : LSP)
			08 - Neck
			09 - Top Head
			10 - Right Wrist
			11 - Right Elbow
			12 - Right Shoulder
			13 - Left Shoulder
			14 - Left Elbow
			15 - Left Wrist
	# TODO : Modify selection of joints for Training
	
	How to generate Dataset:
		Create a TEXT file with the following structure:
			image_name.jpg joint locations
			joint:
				The name of the 'joint'
 			locations :
				Sequence of x y for the joint
				/!\ for now, must be same length as number of joints, but fix this in future
				
	The Generator will read the TEXT file to create a dictionary
	Then 2 options are available for training:
		Store image/heatmap arrays (numpy file stored in a folder: need disk space but faster reading)
		Generate image/heatmap arrays when needed (Generate arrays while training, increase training time - Need to compute arrays at every iteration) 
	"""
	def __init__(self, joints_name = None, img_dir=None, train_data_file = None, remove_joints = None):
		""" Initializer
		Args:
			joints_name			: List of joints condsidered
			img_dir				: Directory containing every images
			train_data_file		: Text file with training set data
			remove_joints		: Joints List to keep (See documentation)
		"""
		if joints_name == None:
			self.joints_list = ['0','1','2','3','4','5','6','7','8','9']

		else:
			self.joints_list = joints_name
		self.toReduce = False
		if remove_joints is not None:
			self.toReduce = True
			self.weightJ = remove_joints
		
		self.letter = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
		self.img_dir = img_dir
		self.train_data_file = train_data_file
		self.images = os.listdir(img_dir)
	
	# --------------------Generator Initialization Methods ---------------------
	
	
	def _reduce_joints(self, joints):
		""" Select Joints of interest from self.weightJ
		"""
		j = []
		for i in range(len(self.weightJ)):
			if self.weightJ[i] == 1:
				j.append(joints[2*i])
				j.append(joints[2*i + 1])
		return j
	
	def _create_train_table(self):
		""" Create Table of samples from TEXT file
		"""
		self.train_table = []
		self.no_intel = []
		self.data_dict = {}
		input_file = open(self.train_data_file, 'r')
		print('READING TRAIN DATA')
		#### for each line, check if first already exists in the system
		#### 	if so,
		for line in input_file:
			line = line.strip()
			line = line.split(' ')
			name = line[0]
			#print(name)
			if name in self.data_dict: # if name is already in data_dict
				joint = line[1]
				locs = list(map(int, line[2:]))
				locs = np.reshape(locs, (-1, 2))
				self.data_dict[name].append(locs)
			# self.data_dict[key] = {'locations': locations} APPEND INSTEAD
			# self.train_table.append(name) DON'T ADD TO TRAIN_TABLE
			else: # ie name isn't already in data_dict
				joint = line[1]
				locs = list(map(int, line[2:]))
				locs = np.reshape(locs, (-1, 2))
				self.data_dict[name] = [locs]
				self.train_table.append(name)

		input_file.close()
		#self.train_table = list(set(self.train_table)) # remove duplicates -- each image is ONE data point
		#print(self.train_table) #####
	
	def _randomize(self):
		""" Randomize the set
		"""
		random.shuffle(self.train_table)
		#print(self.train_table)
	
	def _complete_sample(self, name):
		""" Check if a sample has no missing value
		Args:
			name 	: Name of the sample
		"""
		### Hannah -- took out this condition because in the current context there are NONE without missing ``joints''
		#for i in range(self.data_dict[name]['joints'].shape[0]):
			#if np.array_equal(self.data_dict[name]['joints'][i],[-1,-1]):
				#return False
		return True
	
	def _give_batch_name(self, batch_size = 16, set = 'train'):
		""" Returns a List of Samples
		Args:
			batch_size	: Number of sample wanted
			set				: Set to use (valid/train)
		"""
		list_file = []
		for i in range(batch_size):
			if set == 'train':
				list_file.append(random.choice(self.train_set))
			elif set == 'valid':
				list_file.append(random.choice(self.valid_set))
			else:
				print('Set must be : train/valid')
				break
		return list_file
		
	
	def _create_sets(self, validation_rate = 0.1):
		""" Select Elements to feed training and validation set 
		Args:
			validation_rate		: Percentage of validation data (in ]0,1[, don't waste time use 0.1)
		"""
		sample = len(self.train_table)
		print("sample: "+str(sample))
		#print(self.train_table)
		valid_sample = int(sample * validation_rate)
		self.train_set = self.train_table[:sample - valid_sample]
		self.valid_set = []
		preset = self.train_table[sample - valid_sample:]
		print('START SET CREATION')
		for elem in preset:
			if self._complete_sample(elem):
				self.valid_set.append(elem)
			else:
				self.train_set.append(elem)
		print('SET CREATED')
		np.save('Dataset-Validation-Set', self.valid_set)
		np.save('Dataset-Training-Set', self.train_set)
		#print("trainset: "+str(self.train_set))
		#print("validset: "+str(self.valid_set))
		print('--Training set :', len(self.train_set), ' samples.')
		print('--Validation set :', len(self.valid_set), ' samples.')
	
	def generateSet(self, rand = False):
		""" Generate the training and validation set
		Args:
			rand : (bool) True to shuffle the set
		"""
		self._create_train_table()
		if rand:
			self._randomize()
		self._create_sets()
	
	# ---------------------------- Generating Methods --------------------------	
	
	
	def _makeGaussian(self, height, width, sigma = 3, center=None):
		""" Make a square gaussian kernel.
		size is the length of a side of the square
		sigma is full-width-half-maximum, which
		can be thought of as an effective radius.
		"""
		x = np.arange(0, width, 1, float)
		y = np.arange(0, height, 1, float)[:, np.newaxis]
		if center is None:
			x0 =  width // 2
			y0 = height // 2
		else:
			x0 = center[0]
			y0 = center[1]
		return np.exp(-4*np.log(2) * ((x-x0)**2 + (y-y0)**2) / sigma**2)
	
	def _generate_hm(self, height, width, joints, locations):
		""" Generate a full Heap Map for every joints in an array
		Args:
			height			: Wanted Height for the Heat Map
			width			: Wanted Width for the Heat Map
			joints			: Array of Joints
			locations		: list of lists of locations (for each joint) HANNAH
		"""
		num_joints = len(joints)
		num_tokens = len(locations[0])*20
		hm = np.zeros((height, width, num_joints, num_tokens), dtype = np.float32)
		for type in range(num_joints):
			#if not(np.array_equal(joints[i], [-1,-1])) and weight[i] == 1:
			#s = int(np.sqrt(maxlenght) * maxlenght * 10 / 4096) + 2
			s = int(np.sqrt(width) * width * 10 / 4096) - 5 # CHANGED FROM +2, -5 for "280-small", -10 for "280-tiny" HANNAH
			for token in range(len(locations[type])):
				#print(locations[type][token][0])
				if locations[type][token][0] < 1:
					hm[:, :, type, token] = np.zeros((height, width))
				else:
					hm[:,:,type,token] = self._makeGaussian(height, width, sigma= s, center= (locations[type][token][0], locations[type][token][1]))
		# have hm of shape [height,width,types,tokens]
		# need to combine all the tokens for each type (simple addition, since they're all zeros otherwise?
		condensed_hm = np.zeros((height, width, num_joints), dtype = np.float32)
		for type in range(num_joints):
			for token in range(num_tokens):
				condensed_hm[:,:,type] = condensed_hm[:,:,type] + hm[:,:,type,token]
		return condensed_hm
		
	def _crop_data(self, height, width, box, joints, boxp = 0.05):
		""" Automatically returns a padding vector and a bounding box given
		the size of the image and a list of joints.
		Args:
			height		: Original Height
			width		: Original Width
			box			: Bounding Box
			joints		: Array of joints
			boxp		: Box percentage (Use 20% to get a good bounding box)
		"""
		padding = [[0,0],[0,0],[0,0]]
		j = np.copy(joints)
		if box[0:2] == [-1,-1]:
			j[joints == -1] = 1e5
			box[0], box[1] = min(j[:,0]), min(j[:,1])
		crop_box = [box[0] - int(boxp * (box[2]-box[0])), box[1] - int(boxp * (box[3]-box[1])), box[2] + int(boxp * (box[2]-box[0])), box[3] + int(boxp * (box[3]-box[1]))]
		if crop_box[0] < 0: crop_box[0] = 0
		if crop_box[1] < 0: crop_box[1] = 0
		if crop_box[2] > width -1: crop_box[2] = width -1
		if crop_box[3] > height -1: crop_box[3] = height -1
		new_h = int(crop_box[3] - crop_box[1])
		new_w = int(crop_box[2] - crop_box[0])
		crop_box = [crop_box[0] + new_w //2, crop_box[1] + new_h //2, new_w, new_h]
		if new_h > new_w:
			bounds = (crop_box[0] - new_h //2, crop_box[0] + new_h //2)
			if bounds[0] < 0:
				padding[1][0] = abs(bounds[0])
			if bounds[1] > width - 1:
				padding[1][1] = abs(width - bounds[1])
		elif new_h < new_w:
			bounds = (crop_box[1] - new_w //2, crop_box[1] + new_w //2)
			if bounds[0] < 0:
				padding[0][0] = abs(bounds[0])
			if bounds[1] > width - 1:
				padding[0][1] = abs(height - bounds[1])
		crop_box[0] += padding[1][0]
		crop_box[1] += padding[0][0]
		return padding, crop_box
	
	def _crop_img(self, img, padding, crop_box):
		""" Given a bounding box and padding values return cropped image
		Args:
			img			: Source Image
			padding	: Padding
			crop_box	: Bounding Box
		"""
		img = np.pad(img, padding, mode = 'constant')
		max_lenght = max(crop_box[2], crop_box[3])
		img = img[crop_box[1] - max_lenght //2:crop_box[1] + max_lenght //2, crop_box[0] - max_lenght // 2:crop_box[0] + max_lenght //2]
		return img
		
	def _crop(self, img, hm, padding, crop_box):
		""" Given a bounding box and padding values return cropped image and heatmap
		Args:
			img			: Source Image
			hm			: Source Heat Map
			padding	: Padding
			crop_box	: Bounding Box
		"""
		img = np.pad(img, padding, mode = 'constant')
		hm = np.pad(hm, padding, mode = 'constant')
		max_lenght = max(crop_box[2], crop_box[3])
		img = img[crop_box[1] - max_lenght //2:crop_box[1] + max_lenght //2, crop_box[0] - max_lenght // 2:crop_box[0] + max_lenght //2]
		hm = hm[crop_box[1] - max_lenght //2:crop_box[1] + max_lenght//2, crop_box[0] - max_lenght // 2:crop_box[0] + max_lenght // 2]
		return img, hm
	
	def _relative_joints(self, box, joints, to_size = 64):
		""" Convert Absolute joint coordinates to crop box relative joint coordinates
		(Used to compute Heat Maps)
		Args:
			box			: Bounding Box 
			padding	: Padding Added to the original Image
			to_size	: Heat Map wanted Size
		"""
		new_j = copy.deepcopy(joints)
		#print("joints", joints)
		#print("new_j before", new_j)
		max_l = max(box[2], box[3])
		#new_j = new_j + [padding[1][0], padding[0][0]]
		#new_j = new_j - [box[0] - max_l //2, box[1] - max_l //2]
		#print(new_j.shape)
		#print(new_j[0])
		for type in range(len(new_j)):
			for token in range(len(new_j[type])):
				#print(new_j[type][token])
				#print(new_j[0][elem][0])
				if new_j[type][token][0] > 0:
					#print("before", new_j[type][token])
					new_j[type][token][0] = (new_j[type][token][0] * to_size) / (max_l + 0.0000001)
					new_j[type][token][1] = (new_j[type][token][1] * to_size) / (max_l + 0.0000001)
					#print("after", new_j[type][token])
				#new_j = (new_j * to_size) / (max_l + 0.0000001)
		#print("new_j after", new_j)
		#print("new_j as type int32", new_j.astype(np.int32))
		return new_j #.astype(np.int32)
		
		
	def _augment(self,img, hm, max_rotation = 30):
		""" # TODO : IMPLEMENT DATA AUGMENTATION 
		"""
		if random.choice([0,1]): 
			r_angle = np.random.randint(-1*max_rotation, max_rotation)
			img = 	transform.rotate(img, r_angle, preserve_range = True)
			hm = transform.rotate(hm, r_angle)
		return img, hm
	
	# ----------------------- Batch Generator ----------------------------------
	
	def _generator(self, batch_size = 16, stacks = 4, set = 'train', stored = False, normalize = True, debug = False):
		""" Create Generator for Training
		Args:
			batch_size		: Number of images per batch
			stacks			: Number of stacks/module in the network
			set				: Training/Testing/Validation set # TODO: Not implemented yet
			stored			: Use stored Value # TODO: Not implemented yet
			normalize		: True to return Image Value between 0 and 1
			_debug			: Boolean to test the computation time (/!\ Keep False)
		# Done : Optimize Computation time 
			16 Images --> 1.3 sec (on i7 6700hq)
		""" 
		while True:
			if debug:
				t = time.time()
			train_img = np.zeros((batch_size, 256,256,3), dtype = np.float32)
			train_gtmap = np.zeros((batch_size, stacks, 64, 64, len(self.joints_list)), np.float32)
			files = self._give_batch_name(batch_size= batch_size, set = set)
			for i, name in enumerate(files):
				if name[:-1] in self.images:
					try :
						img = self.open_img(name)
						#locations = self.data_dict[name]['locations']
						#box = self.data_dict[name]['box']
						#weight = self.data_dict[name]['weights']
						#if debug:
							#print(box)
						#padd, cbox = self._crop_data(img.shape[0], img.shape[1], box, joints, boxp = 0.2)
						#if debug:
							#print(cbox)
							#print('maxl :', max(cbox[2], cbox[3]))
						#new_j = self._relative_joints(cbox,padd, joints, to_size=64)
						box = [0, 0, img.shape[0], img.shape[1]]
						locations = self.data_dict[name]
						resized_locs = self._relative_joints(box, locations, to_size=64)
						# print(str(resized_locs))
						#rhm = self._generate_hm(256, 256, self.joints_list, resized_locs)
						hm = self._generate_hm(64, 64, self.joints_list, resized_locs)
						#img = self._crop_img(img, padd, cbox)
						img = img.astype(np.uint8)
						# On 16 image per batch
						# Avg Time -OpenCV : 1.0 s -skimage: 1.25 s -scipy.misc.imresize: 1.05s
						img = scm.imresize(img, (256,256))
						# Less efficient that OpenCV resize method
						#img = transform.resize(img, (256,256), preserve_range = True, mode = 'constant')
						# May Cause trouble, bug in OpenCV imgwrap.cpp:3229
						# error: (-215) ssize.area() > 0 in function cv::resize
						#img = cv2.resize(img, (256,256), interpolation = cv2.INTER_CUBIC)
						img, hm = self._augment(img, hm)
						hm = np.expand_dims(hm, axis = 0)
						hm = np.repeat(hm, stacks, axis = 0)
						if normalize:
							train_img[i] = img.astype(np.float32) / 255
						else :
							train_img[i] = img.astype(np.float32)
						train_gtmap[i] = hm
					except :
						i = i-1
				else:
					i = i - 1
			if debug:
				print('Batch : ',time.time() - t, ' sec.')
			yield train_img, train_gtmap
			
	def _aux_generator(self, batch_size = 16, stacks = 4, normalize = True, sample_set = 'train'):
		""" Auxiliary Generator
		Args:
			See Args section in self._generator
		"""
		while True:
			train_img = np.zeros((batch_size, 256,256,3), dtype = np.float32)
			train_gtmap = np.zeros((batch_size, stacks, 64, 64, len(self.joints_list)), np.float32)
			#train_weights = np.zeros((batch_size, len(self.joints_list)), np.float32)
			i = 0
			while i < batch_size:
				try:
					if sample_set == 'train':
						name = random.choice(self.train_set)
					elif sample_set == 'valid':
						name = random.choice(self.valid_set)
					#locations = self.data_dict[name]['locations']
					#box = self.data_dict[name]['box']
					#weight = np.asarray(self.data_dict[name]['weights'])
					#train_weights[i] = weight
					img = self.open_img(name)
					#print("img fine")
					#padd, cbox = self._crop_data(img.shape[0], img.shape[1], box, joints, boxp = 0.2)
					#new_j = self._relative_joints(cbox,padd, joints, to_size=64)
					box = [0, 0, img.shape[0], img.shape[1]]
					#print("box fine", box)
					locations = self.data_dict[name]
					#print("locations fine")
					resized_locs = self._relative_joints(box, locations, to_size=64)
					#print("resized_locs fine")
					#print(str(resized_locs))
					#rhm = self._generate_hm(256, 256, self.joints_list, resized_locs)
					hm = self._generate_hm(64, 64, self.joints_list, resized_locs)
					#print("augment fine")
					#img = self._crop_img(img, padd, cbox)
					img = img.astype(np.uint8)
					img = scm.imresize(img, (256,256))
					#print("img resized fine")
					#img, hm = self._augment(img, hm)
					#print("img, hm augment fine")
					hm = np.expand_dims(hm, axis = 0)
					#print("hm expanded dims fine")
					hm = np.repeat(hm, stacks, axis = 0)
					#print("hm repeat stacks fine")
					if normalize:
						train_img[i] = img.astype(np.float32) / 255
					else :
						train_img[i] = img.astype(np.float32)
					train_gtmap[i] = hm
					#print("train_gtmap fine")
					i = i + 1
				except :
					print('error file: ', name)
			yield train_img, train_gtmap #train_weights
					
	def generator(self, batchSize = 16, stacks = 4, norm = True, sample = 'train'):
		""" Create a Sample Generator
		Args:
			batchSize 	: Number of image per batch 
			stacks 	 	: Stacks in HG model
			norm 	 	 	: (bool) True to normalize the batch
			sample 	 	: 'train'/'valid' Default: 'train'
		"""
		return self._aux_generator(batch_size=batchSize, stacks=stacks, normalize=norm, sample_set=sample)
	
	# ---------------------------- Image Reader --------------------------------				
	def open_img(self, name, color = 'RGB'):
		""" Open an image 
		Args:
			name	: Name of the sample
			color	: Color Mode (RGB/BGR/GRAY)
		"""
		if name[-1] in self.letter:
			name = name[:-1]
		img = cv2.imread(os.path.join(self.img_dir, name))
		if color == 'RGB':
			img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
			return img
		elif color == 'BGR':
			return img
		elif color == 'GRAY':
			img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		else:
			print('Color mode supported: RGB/BGR. If you need another mode do it yourself :p')
	
	def plot_img(self, name, plot = 'cv2'):
		""" Plot an image
		Args:
			name	: Name of the Sample
			plot	: Library to use (cv2: OpenCV, plt: matplotlib)
		"""
		if plot == 'cv2':
			img = self.open_img(name, color = 'BGR')
			cv2.imshow('Image', img)
		elif plot == 'plt':
			img = self.open_img(name, color = 'RGB')
			plt.imshow(img)
			plt.show()
	
	def test(self, toWait = 0.9):
		""" TESTING METHOD
		You can run it to see if the preprocessing is well done.
		Wait few seconds for loading, then diaporama appears with image and highlighted joints
		/!\ Use Esc to quit
		Args:
			toWait : In sec, time between pictures
		"""
		self._create_train_table()
		self._create_sets()
		size = 256
		for i in range(len(self.train_set)):
			name = self.train_set[i]
			img = self.open_img(name)
			#w = self.data_dict[self.train_set[i]]['weights']
			#padd, box = self._crop_data(img.shape[0], img.shape[1], self.data_dict[self.train_set[i]]['box'], self.data_dict[self.train_set[i]]['joints'], boxp= 0.0)
			#new_j = self._relative_joints(box,padd, self.data_dict[self.train_set[i]]['joints'], to_size=256)
			box = [0,0,img.shape[0],img.shape[1]]
			locations = self.data_dict[name]
			resized_locs = self._relative_joints(box, locations, to_size=size)
			#print(str(resized_locs))
			rhm = self._generate_hm(size, size, self.joints_list, resized_locs)
			#rimg = self._crop_img(img, padd, box)
			# See Error in self._generator
			#rimg = cv2.resize(rimg, (256,256))
			rimg = scm.imresize(img, (size,size))
			#rhm = np.zeros((256,256,16))
			#for i in range(16):
			#	rhm[:,:,i] = cv2.resize(rHM[:,:,i], (256,256))
			grimg = cv2.cvtColor(rimg, cv2.COLOR_RGB2GRAY)
			cv2.imshow('image', grimg / 255 + np.sum(rhm,axis = 2))
			time.sleep(toWait)
			#for type in range(len(resized_locs[2])):
				#time.sleep(toWait)
				#cv2.imshow('image', grimg / 255 + rhm[:,:,type])
				# Wait

			if cv2.waitKey(1) == 27:
				print('Ended')
				cv2.destroyAllWindows()
				break
	
	
	
	# ------------------------------- PCK METHODS-------------------------------
	def pck_ready(self, idlh = 3, idrs = 12, testSet = None):
		""" Creates a list with all PCK ready samples
		(PCK: Percentage of Correct Keypoints)
		"""
		id_lhip = idlh
		id_rsho = idrs
		self.total_joints = 0
		self.pck_samples = []
		for s in self.data_dict.keys():
			if testSet == None:
				if self.data_dict[s]['weights'][id_lhip] == 1 and self.data_dict[s]['weights'][id_rsho] == 1:
					self.pck_samples.append(s)
					wIntel = np.unique(self.data_dict[s]['weights'], return_counts = True)
					self.total_joints += dict(zip(wIntel[0], wIntel[1]))[1]
			else:
				if self.data_dict[s]['weights'][id_lhip] == 1 and self.data_dict[s]['weights'][id_rsho] == 1 and s in testSet:
					self.pck_samples.append(s)
					wIntel = np.unique(self.data_dict[s]['weights'], return_counts = True)
					self.total_joints += dict(zip(wIntel[0], wIntel[1]))[1]
		print('PCK PREPROCESS DONE: \n --Samples:', len(self.pck_samples), '\n --Num.Joints', self.total_joints)
	
	def getSample(self, sample = None):
		""" Returns information of a sample
		Args:
			sample : (str) Name of the sample
		Returns:
			img: RGB Image
			new_j: Resized Joints 
			w: Weights of Joints
			joint_full: Raw Joints
			max_l: Maximum Size of Input Image
		"""
		if sample != None:
			try:
				#joints = self.data_dict[sample]['joints']
				#box = self.data_dict[sample]['box']
				#w = self.data_dict[sample]['weights']
				img = self.open_img(sample)
				#padd, cbox = self._crop_data(img.shape[0], img.shape[1], box, joints, boxp = 0.2)
				box = [0, 0, img.shape[0], img.shape[1]]
				locations = self.data_dict[sample]
				resized_locs = self._relative_joints(box, locations, to_size=256)
				# print(str(resized_locs))
				#rhm = self._generate_hm(256, 256, self.joints_list, resized_locs)
				#new_j = self._relative_joints(cbox,padd, joints, to_size=256)
				joint_full = np.copy(locations)
				max_l = max(box[2], box[3])
				#joint_full = joint_full + [padd[1][0], padd[0][0]]
				#joint_full = joint_full - [box[0] - max_l //2,box[1] - max_l //2]
				#img = self._crop_img(img, padd, cbox)
				img = img.astype(np.uint8)
				img = scm.imresize(img, (256,256))
				return img, resized_locs, joint_full, max_l ### REMOVED W BECAUSE NO LONGER USED
			except:
				return False
		else:
			print('Specify a sample name')
				
		
		