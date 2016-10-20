"""
Convolutional Neural Network
---
@author TaoPR (github.com/starcolon)
"""

import time
from theano import *
from theano import tensor as T
from scipy import *
import numpy as np
import lasagne
import _pickle as pickle
from lasagne import layers
from lasagne.updates import adagrad
from lasagne.objectives import *
from nolearn.lasagne import NeuralNet
from nolearn.lasagne import visualize
from termcolor import colored
from . import *

class CNN():

  """
  @param {int} dimension of feature vector
  """
  def __init__(self, image_dim, final_vec_dim):
    input_dim  = (None,) + image_dim

    # Create initial nets, one per final vector element
    self.nets = []
    self.input_layers = []
    for i in range(final_vec_dim):
      l_input = layers.InputLayer(shape=input_dim)
      l_conv1 = layers.Conv2DLayer(l_input, 32, (5,5))
      l_conv2 = layers.Conv2DLayer(l_conv1, 32, (3,3))
      l_pool  = layers.MaxPool2DLayer(l_conv2, (5,5), stride=2)
      l_1d1   = layers.DenseLayer(l_pool, 64)
      l_1d2   = layers.DenseLayer(l_1d1, 1)

      self.nets.append(l_1d2)
      self.input_layers.append(l_input)

  # Train the neural net
  # @param {Matrix} trainset X
  # @param {Vector} trainset y
  # @param {Matrix} validation set X
  # @param {Vector} validation set y
  # @param {int} batch size
  # @param {int} number of epochs to run
  # @param {list[double]} learning rates (non-negative, non-zero)
  # @param {str} path to save model
  def train(self,X,y,X_,y_,batch_size=100,num_epochs=100,learn_rate=[0.01,0.05,0.2,0.05],model_path='model.cnn'):

    # Symbolic I/O of the networks
    inputx  = [n.input_var for n in self.input_layers]
    outputy = [T.dmatrix('y') for _ in range(len(self.nets))] # Expected output
    output  = [layers.get_output(n) for n in self.nets] # Actual output

    print('... X : ', X.shape)
    print('... y : ', y.shape)
    print('... X_ : ', X_.shape)
    print('... y_ : ', y_.shape)

    # Minimising RMSE with Adagradient
    print(colored('...Preparing measurement functions','green'))
    loss   = [T.mean((output[i] - outputy[i])**2) for i in range(len(self.nets))]
    params = [layers.get_all_params(n) for n in self.nets]
    update = [adagrad(loss[i], params[i], learn_rate[i]) for i in range(len(self.nets))]

    print(colored('...Preparing training functions','green'))
    train  = [theano.function(
      [inputx[i], outputy[i]],
      loss[i], 
      updates=update[i]
      ) for i in range(len(self.nets))]
    
    gen_output = [theano.function([inputx[i]], output[i]) for i in range(len(self.nets))]

    print(colored('...Training started','green'))
    for epoch in range(num_epochs):
      with open('loss.csv', 'a+') as tcsv:
        print('...[Ep] #', epoch)
        
        t0       = time.time()
        b0,bN,bi = 0, batch_size, 0

        losses_train = None
        losses_val   = None

        # Each batch
        while bN < X.shape[0]:
          print('......batch #', bi, ' ({0}~{1})'.format(b0,bN))

          ll, llv = [],[]
          
          # Train each model separately with the same samples
          for i in range(len(train)):
            print('......(model #{0})'.format(i))
            _x = X[b0:bN]
            _y = y[b0:bN, i].reshape(-1,1)

            train[i](_x, _y)

            # Measure training loss (RMSE)
            _output  = gen_output[i](_x)
            _loss    = np.mean((_output[i] - _y)**2)
            # Measure validation loss (RMSE)
            _outputv = gen_output[i](X_)
            _lossv   = np.mean((_outputv[i] - y_[:, i].reshape(-1,1))**2)

            ll.append(_loss)
            llv.append(_lossv)

          b0 += batch_size
          bN += batch_size
          bi += 1

          # Collect the training loss values over batches
          if losses_train is not None:
            losses_train = np.vstack((losses_train, np.array(ll)))
            losses_val   = np.vstack((losses_val,   np.array(llv)))
          else:
            losses_train = np.array([ll])
            losses_val   = np.array([llv])

        # All batches finished, collect loss values
        losses_train = np.mean(losses_train, axis=0).tolist()
        losses_val   = np.mean(losses_val, axis=0).tolist()

        losses_train = ['{0:.4f}'.format(d) for d in losses_train]
        losses_val   = ['{0:.4f}'.format(d) for d in losses_val]

        print('...Training Loss   : ', ','.join(losses_train))
        print('...Validation Loss : ', ','.join(losses_val))

        t1 = time.time()
        print(colored('...{0:.1f} s elapsed, {1} batches processed'.format(t1-t0, bi), 'yellow'))

        # Shuffle the trainset
        print('...Shuffling the trainset')
        rd = np.arange(len(y))
        np.random.shuffle(rd)
        X = X[rd]
        y = y[rd]

        # Save the model every 10 epochs
        if epoch % 10 == 0 and epoch>0:
          self.save(model_path)

        # Save losses
        tcsv.write('EP#{0},'.format(epoch) + '\n')
        tcsv.write('T:' + ','.join(losses_train) + '\n')
        tcsv.write('V:' + ','.join(losses_val) + '\n')

  def predict(self,candidates):
    # TAOTODO: Re-implement
    gen_output = theano.function([inputx], output)

  def save(self,path):
    model = [self.nets,
             self.input_layers]
    with open(path, 'wb') as f:
      print(colored('Saving the model at {}'.format(path),'green'))
      pickle.dump(model, f, -1)
      print('...Done!')

  @staticmethod
  def load(path):
    with open(path, 'rb') as f:
      print(colored('Loading the model at {}'.format(path),'green'))
      return pickle.load(f)




