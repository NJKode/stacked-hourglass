# -*- coding: utf-8 -*-
"""
Created on Sun May 28 17:39:00 2017

@author: Walid Benbihi
@mail: w.benbihi (at) gmail.com
"""

########################################
#	           Parameters
########################################


# Directory (do not forget the last '/')

img_dir 			= '~/stacked-hourglass/dataMNIST4-5/' # Was '~/images/' # Directory of image dataset (.png, .jpg)
data_dir 			= '~/stacked-hourglass/dataMNIST4-5csv/' # Was '~/data/ # Directory of .csv files
train_dir 		= '~/logs/train/'	# Path to save training logs
test_dir 			= '~/logs/test/'	# Path to save testing logs
processed_dir 	= '~/arrays/'		# Directory of processed images (.npy)

# TensorFlow Parameters

gpu = '/gpu:0'			# Indicates which GPU to use (can be replace by a CPU) (was 0)
cpu = '/cpu:0'			# Indicates which CPU to use (only use CPU)


# Training Parameters

learning_rate 		= 2.5e-4    # Learning Rate
nEpochs 		    = 200		# (Was 30) Number of epochs
iter_by_epoch 		= 1000		# (Was 1000) Number of batch to train in one epoch
batch_size 		    = 16		    # (Was 16) Batch Size per iteration
limit_train_test 	= 24000	    # Index of separation between training and testing set

step_to_save 		= 1	        # (Was 500) Step to save summaries on TensorBoard (should be lower than iter_by_epoch)
random_angle_max 	= 30		# Max of random rotation
random_angle_min 	= -30		# Min of random rotation

# Hourglass Parameters

nbStacks            = 8	 			# Number of stacks
outDim 		        = 10			# Number of output channels (how many joints) (was 16)
nFeat 		        = 56			# Number of feature channels (was 256)
nLow 		        = 4 			# Number of downsampling by stacks (3 or 4 for better results)
nModule             = 1				# Number of upsampling iterations (Not implemented yet)






