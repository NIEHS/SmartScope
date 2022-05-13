import os 
import pickle
import sys
import numpy as np 
import torch
from PIL import Image 
from torch.utils.data import Dataset 
from utils.mypath import MyPath 
from torchvision.datasets.utils import check_integrity, download_and_extract_archive
from utils.preprocess import normalize_images

class SQUARE(Dataset):
	def __init__(self, data_dir=MyPath.db_root_dir('squares'), train=True, transform=None):
		self.train = train 
		label = np.load('/hpc/home/qh36/research/qh36/automation/hole_classification/new_labels.npy')
		data = np.load(data_dir)
		data = normalize_images(data)
		np.random.seed(10)
		self.transform = transform
		perm = np.random.permutation(data.shape[0])
		if self.train:
			self.data = data[perm[:int(data.shape[0]*1)]]
			self.labels = label[perm[:int(data.shape[0]*1)]]
		else:
			self.data = data[perm[:int(data.shape[0]*1)]]
			self.labels = label[perm[:int(data.shape[0]*1)]]

		#self.data = data 
		self.size = len(self.data)

	def __len__(self):
		return self.size 

	def __getitem__(self, idx):
		img = Image.fromarray(self.data[idx],'L')
		target = self.labels[idx]
		img_size = (self.data[idx].shape[0],self.data[idx].shape[1])
		if self.transform is not None:
			img = self.transform(img)
		out = {'image': img, 'target': torch.tensor(target), 'meta': {'img_size': img_size, 'index': idx}}
		return out

	def get_image(self, idx):
		img = self.data[idx]
		return img


