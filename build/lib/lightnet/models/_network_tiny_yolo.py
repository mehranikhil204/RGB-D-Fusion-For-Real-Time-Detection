#
#   Darknet Tiny YOLOv2 model
#   Copyright EAVISE
#

from collections import OrderedDict, Iterable
import torch.nn as nn
import lightnet.network as lnn

__all__ = ['TinyYolo']


class TinyYolo(lnn.module.Darknet):
    """ Tiny Yolo v2 implementation :cite:`yolo_v2`.

    Args:
        num_classes (Number, optional): Number of classes; Default **20**
        input_channels (Number, optional): Number of input channels; Default **3**
        anchors (list, optional): 2D list with anchor values; Default **Tiny yolo v2 anchors**

    Attributes:
        self.stride: Subsampling factor of the network (input dimensions should be a multiple of this number)
        self.remap_darknet: Remapping rules for weights from the `~lightnet.models.Darknet` model.
    """
    stride = 32
    remap_darknet = [
        (r'^layers.0.(\d+_)',   r'layers.\1'),  # All base layers (1-13)
    ]

    def __init__(self, num_classes=20, input_channels=3, anchors=[(1.08, 1.19), (3.42, 4.41), (6.63, 11.38), (9.42, 5.11), (16.62, 10.52)]):
        super().__init__()
        if not isinstance(anchors, Iterable) and not isinstance(anchors[0], Iterable):
            raise TypeError('Anchors need to be a 2D list of numbers')

        # Parameters
        self.num_classes = num_classes
        self.input_channels = input_channels
        self.anchors = anchors

        # Network
        self.layers = nn.Sequential(
            OrderedDict([
                ('1_convbatch',     lnn.layer.Conv2dBatchReLU(input_channels, 16, 3, 1, 1)),
                ('2_max',           nn.MaxPool2d(2, 2)),
                ('3_convbatch',     lnn.layer.Conv2dBatchReLU(16, 32, 3, 1, 1)),
                ('4_max',           nn.MaxPool2d(2, 2)),
                ('5_convbatch',     lnn.layer.Conv2dBatchReLU(32, 64, 3, 1, 1)),
                ('6_max',           nn.MaxPool2d(2, 2)),
                ('7_convbatch',     lnn.layer.Conv2dBatchReLU(64, 128, 3, 1, 1)),
                ('8_max',           nn.MaxPool2d(2, 2)),
                ('9_convbatch',     lnn.layer.Conv2dBatchReLU(128, 256, 3, 1, 1)),
                ('10_max',          nn.MaxPool2d(2, 2)),
                ('11_convbatch',    lnn.layer.Conv2dBatchReLU(256, 512, 3, 1, 1)),
                ('12_max',          lnn.layer.PaddedMaxPool2d(2, 1, (0, 1, 0, 1))),
                ('13_convbatch',    lnn.layer.Conv2dBatchReLU(512, 1024, 3, 1, 1)),
                ('14_convbatch',    lnn.layer.Conv2dBatchReLU(1024, 1024, 3, 1, 1)),
                ('15_conv',         nn.Conv2d(1024, len(self.anchors)*(5+self.num_classes), 1, 1, 0)),
            ])
        )
