import os
import csv

import numpy as np
import tensorflow as tf
from PIL import Image


class TCData(object):
    def __init__(self, image_dir, label_filename, conf):
        self.image_dir = image_dir
        self.label_filename = label_filename
        self.batch_size = conf.batch_size
        self.labels = []
        self.images = []

        self.language_set = []
        if 'language_list' in conf.values() and len(conf.language_list) > 1:
            self.language_set = conf.language_list

    def load_data(self):
        with open(self.label_filename) as label_file:
            csv_reader = csv.reader(label_file, delimiter=',')
            for audio, label in csv_reader:
                audio_filename = os.path.splitext(audio)[0]
                image_path = os.path.join(self.image_dir, '{}.png'.format(audio_filename))
                self.images.append(image_path)

                # Store labels in a global
                if label not in self.language_set:
                    self.language_set.append(label)
                label_index = self.language_set.index(label)

                self.labels.append(label_index)
        tf.logging.info("Language index: {}".format(self.language_set))

    def lang_index(self, lang):
        """Return the index of the given language."""
        return self.language_set.index(lang)

    def get_data(self, use_percent, tail=False):
        """Return the first (or the last) use_percent percent of data and
        its labels.
        """
        start = None
        end = int(round(len(self.images) * use_percent / 100.))
        if tail:
            start, end = -end, start
        return self.images[start:end], self.labels[start:end]

    @staticmethod
    def instance_as_tensor(image_name, label=None):
        """Convert a single training/prediction instance into a tensor."""
        img_file = tf.read_file(image_name)
        image = tf.image.decode_png(img_file, channels=0)
        image = tf.cast(image, tf.float32)
        image_data = tf.transpose(image[:128, :] / 256.)

        if label is not None:
            label = tf.cast(label, tf.int32)

        return {'sgram': image_data}, label
