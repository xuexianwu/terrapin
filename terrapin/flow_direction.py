import numpy as np
from skimage.morphology import reconstruction

def d8(dem):
	"""
	Implements D8 Flow Direction algorithm
	D8 Flow Direction Coding: 0 - East, 1 - Northeast, 2 - North, 3 - Northwest , 4 - West, 5 - Southwest, 6 - South, 7 - Southeast.
	"""
	inv_sqrt2 = 1/np.sqrt(2)

	d0 = dem[1:-1,1:-1] - dem[1:-1,2:]
	d1 = (dem[1:-1,1:-1] - dem[:-2,2:]) * inv_sqrt2
	d2 = dem[1:-1,1:-1] - dem[:-2,1:-1]
	d3 = (dem[1:-1,1:-1] - dem[:-2,:-2]) * inv_sqrt2
	d4 = dem[1:-1,1:-1] - dem[1:-1,:-2]
	d5 = (dem[1:-1,1:-1] - dem[2:,:-2]) * inv_sqrt2
	d6 = dem[1:-1,1:-1] - dem[2:,1:-1]
	d7 = (dem[1:-1,1:-1] - dem[2:,2:]) * inv_sqrt2 

	stacked = np.dstack([d0, d1, d2, d3, d4, d5, d6, d7])
	directions = stacked.argmax(axis=2)

	# find indetermate points, argmax returns first occurance of max so lets reverse it 
	# and try again. If the indices don't match then the point is indeterminate
	reversed_indices = 7 - stacked[:,:,::-1].argmax(axis=2) 
	directions[reversed_indices!=directions] = -1

	return directions


def convert_d8_directions(directions, fmt, inverse=False):
	if not fmt:
		return directions

	if fmt not in ['esri', 'taudem', 'degrees', 'radians']:
		raise NotImplementedError('Format %s not implemented' % fmt)

	if inverse:
		if fmt=='esri':
			converted = (8 - (np.log2(directions)).astype(int)) % 8
			converted = converted.squeeze()

		if fmt=='taudem':
			converted = directions - 1

		if fmt=='degrees':
			converted = (directions / 45).astype(int)

		if fmt=='radians':
			converted = (directions / (np.pi * 0.25)).astype(int)

		return converted

	if fmt=='esri':
		convert = np.vectorize(lambda x:2**((8-x)%8))
		converted = convert(directions)

	if fmt=='taudem':
		converted = directions + 1

	if fmt=='degrees':
		converted = directions * 45

	if fmt=='radians':
		converted = directions * np.pi * 0.25

	# maintain indeterminate points
	converted[directions==-1] = -1 

	return converted


def fill_flats(d8):
	# simple method to get rid of indeterminate areas using erosion.
	# ref: http://scikit-image.org/docs/dev/auto_examples/plot_holes_and_peaks.html#example-plot-holes-and-peaks-py

	seed = np.copy(d8)
	seed[d8==-1] = d8.max()
	mask = d8
	filled = reconstruction(seed, mask, method='erosion')

	return filled.astype(int)


class aread8():
	def __init__(self, d8):
		self.visited = set()
		self.accumulation = np.zeros_like(d8)
		self.d8 = d8
		self.padded = np.zeros((d8.shape[0]+2,d8.shape[1]+2))
		self.padded[:] = np.nan
		self.padded[1:-1,1:-1] = d8

	def accumulate(self):
		rows, cols = self.d8.shape
		for i in range(rows):
			for j in range(cols):
				if (i,j) not in self.visited:
					self.area(i,j)

	def area(self, i, j):
		if (i,j) in self.visited:
			return self.accumulation[i,j]
		else:
			self.visited.add((i,j))
			for m, n in self._inflow_nodes(i,j):
				self.accumulation[i,j] += 1
				self.accumulation[i,j] += self.area(m, n) 
			return self.accumulation[i,j]

	def _inflow_nodes(self, i,j):

		mask = np.array([
			[7,  6, 5],
			[0, -1, 4],
			[1,  2, 3]])

		# padded is offset +1,+1 from d8
		m, n = np.where(self.padded[i:i+3,j:j+3] == mask)
				
		return zip(i+m-1, j+n-1)