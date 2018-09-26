#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: load-vgg16.py

from __future__ import print_function
import cv2
import tensorflow as tf
import numpy as np
import os
import six
import argparse

from tensorpack import *
from tensorpack.dataflow.dataset import ILSVRCMeta

enable_argscope_for_module(tf.layers)


def tower_func(image):
    is_training = get_current_tower_context().is_training

    with argscope([tf.layers.conv2d], kernel_size=3, activation=tf.nn.relu, padding='same'):
        x = image
        x = tf.layers.conv2d(x, 64, name='conv1_1')
        x = tf.layers.conv2d(x, 64, name='conv1_2')
        x = tf.layers.max_pooling2d(x, 2, 2, name='pool1')

        x = tf.layers.conv2d(x, 128, name='conv2_1')
        x = tf.layers.conv2d(x, 128, name='conv2_2')
        x = tf.layers.max_pooling2d(x, 2, 2, name='pool2')

        x = tf.layers.conv2d(x, 256, name='conv3_1')
        x = tf.layers.conv2d(x, 256, name='conv3_2')
        x = tf.layers.conv2d(x, 256, name='conv3_3')
        x = tf.layers.max_pooling2d(x, 2, 2, name='pool3')

        x = tf.layers.conv2d(x, 512, name='conv4_1')
        x = tf.layers.conv2d(x, 512, name='conv4_2')
        x = tf.layers.conv2d(x, 512, name='conv4_3')
        x = tf.layers.max_pooling2d(x, 2, 2, name='pool4')

        x = tf.layers.conv2d(x, 512, name='conv5_1')
        x = tf.layers.conv2d(x, 512, name='conv5_2')
        x = tf.layers.conv2d(x, 512, name='conv5_3')
        x = tf.layers.max_pooling2d(x, 2, 2, name='pool5')
        x = tf.layers.flatten(x, name='flatten')

        x = tf.layers.dense(x, 4096, activation=tf.nn.relu, name='fc6')
        x = tf.layers.dropout(x, rate=0.5, name='drop0', training=is_training)
        x = tf.layers.dense(x, 4096, activation=tf.nn.relu, name='fc7')
        x = tf.layers.dropout(x, rate=0.5, name='drop1', training=is_training)
        logits = tf.layers.dense(x, 1000, activation=tf.identity, name='fc8')

    tf.nn.softmax(logits, name='prob')


def run_test(path, input):
    param_dict = dict(np.load(path))
    param_dict = {k.replace('/W', '/kernel').replace('/b', '/bias'): v for k, v in six.iteritems(param_dict)}

    predict_func = OfflinePredictor(PredictConfig(
        inputs_desc=[InputDesc(tf.float32, (None, 224, 224, 3), 'input')],
        tower_func=tower_func,
        session_init=DictRestore(param_dict),
        input_names=['input'],
        output_names=['prob']   # prob:0 is the probability distribution
    ))

    im = cv2.imread(input)
    assert im is not None, input
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    im = cv2.resize(im, (224, 224)).reshape((1, 224, 224, 3)).astype('float32')

    # VGG16 requires channelwise mean substraction
    VGG_MEAN = [103.939, 116.779, 123.68]
    im -= VGG_MEAN[::-1]

    outputs = predict_func(im)[0]
    prob = outputs[0]
    ret = prob.argsort()[-10:][::-1]
    print("Top10 predictions:", ret)

    meta = ILSVRCMeta().get_synset_words_1000()
    print("Top10 class names:", [meta[k] for k in ret])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpu', help='comma separated list of GPU(s) to use.')
    parser.add_argument('--load', required=True,
                        help='.npz model file generated by tensorpack.utils.loadcaffe')
    parser.add_argument('--input', help='an input image', required=True)
    args = parser.parse_args()
    if args.gpu:
        os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu
    run_test(args.load, args.input)
