#
#   Base lightnet network module structure
#   Copyright EAVISE
#

import logging
import re
from collections import OrderedDict
import torch
import torch.nn as nn

__all__ = ['Lightnet']
log = logging.getLogger(__name__)


class Lightnet(nn.Module):
    """ This class provides an abstraction layer on top of :class:`pytorch:torch.nn.Module` and is used as a base for every network implemented in this framework.

    Note:
        If you define **self.layers** as a :class:`pytorch:torch.nn.Sequential` or :class:`pytorch:torch.nn.ModuleList`,
        the default ``forward()`` function can use these layers automatically to run the network.
    """
    def __init__(self):
        super().__init__()
        self.layers = None

    def forward(self, x):
        log.debug('Running default forward function')
        if hasattr(self, 'layers'):
            if isinstance(self.layers, nn.Sequential):
                return self.layers(x)
            elif isinstance(self.layers, nn.ModuleList):
                log.warning('No _forward function defined, looping sequentially over modulelist')
                for _, module in enumerate(self.layers):
                    x = module(x)
                return x
            else:
                raise NotImplementedError(f'No _forward function defined and no default behaviour for this type of layers [{type(self.layers)}]')
        else:
            raise NotImplementedError(f'No _forward function defined and no default behaviour for this network')

    def layer_loop(self, mod=None):
        """ This function will recursively loop over all moduleList and Sequential children.

        Args:
            mod (torch.nn.Module, optional): Module to loop over; Default **self**

        Returns:
            (generator): Iterator that will loop over and yield the different layers
        """
        if mod is None:
            mod = self

        for module in mod.children():
            if isinstance(module, (nn.ModuleList, nn.Sequential)):
                yield from self.layer_loop(module)
            else:
                yield module

    def named_layer_loop(self, mod=None):
        """ Named version of :func:`~lightnet.network.module.Lightnet.layer_loop`

        Args:
            mod (torch.nn.Module, optional): Module to loop over; Default **self**

        Returns:
            (generator): Iterator that will loop over and yield (name, layer) tuples
        """
        if mod is None:
            mod = self

        for name, module in mod.named_children():
            if isinstance(module, (nn.ModuleList, nn.Sequential)):
                yield from self.named_layer_loop(module)
            else:
                yield name, module

    def load(self, weights, strict=True):
        """ This function will load the weights from a file.
        It also allows to load in weights file with only a part of the weights in.

        Args:
            weights_file (str): path to file
            strict (Boolean, optional): Whether the weight file should contain all layers of the model; Default **False**

        Note:
            This function will load the weights to CPU,
            so you should use ``network.to(device)`` afterwards to send it to the device of your choice.
        """
        keys = self.state_dict().keys()
        log.info(f'Loading weights from file [{weights}]')
        state = torch.load(weights, 'cpu')

        if not strict and state.keys() != keys:
            log.warning('Modules not matching, performing partial update')
        self.load_state_dict(state, strict=strict)

    def save(self, weights_file, remap=None):
        """ This function will save the weights to a file.

        Args:
            weights_file (str): path to file
            remap (list, optional): list of remapping tuples, to be able to use the weights from one model in another; Default **None**

        Note:
            The optional ``remap`` parameter expects a list of tuples, containing **('old', 'new')** remapping sequences.
            The remapping sequence can contain strings or regex objects.

            What happens when you supply a remapping list,
            is that this function will loop over the ``state_dict`` of the model and for each parameter of the ``state_dict`` it will loop through the remapping list.
            If the first string or regex of the remapping sequence is found in the ``state_dict`` key, it will be replaced by the second string or regex of that remapping sequence. |br|
            There are two important things to note here:

            - If a key does not match any remapping sequence, it gets discarded. To save all the weights, even if you need no remapping, add a last remapping sequence of **('', '')** which will match with all keys, but not modify them.
            - The remapping sequences or processed in order. This means that if a key matches with a certain remapping sequence, the following sequences will not be considered anymore.
        """
        if remap is not None:
            orig_weights = self.state_dict()
            weights = OrderedDict()

            for k, v in orig_weights.items():
                for r in remap:
                    if re.match(r[0], k) is not None:
                        weights[re.sub(r[0], r[1], k)] = v
                        break

            remap = ' remapped'
        else:
            weights = self.state_dict()
            remap = ''

        torch.save(weights, weights_file)

        log.info(f'Saved{remap} weights as {weights_file}')
