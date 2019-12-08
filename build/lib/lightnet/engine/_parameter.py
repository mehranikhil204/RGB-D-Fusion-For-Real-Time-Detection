#
#   HyperParemeters container class
#   Copyright EAVISE
#

import logging
import importlib.util
from collections import Iterable
import torch

__all__ = ['HyperParameters']
log = logging.getLogger(__name__)


class HyperParameters:
    """ This class is a container for training hyperparameters.
    It allows to save the state of a training and reload it at a later stage.

    Args:
        **kwargs (dict, optional): Keywords arguments that will be set as attributes of the instance and serialized as well

    Attributes:
        self.batch: Number of batches processed; Gets initialized to **0**
        self.epoch: Number of epochs processed; Gets initialized to **0**
        self.*: All arguments passed to the initialization function can be accessed as attributes of this object

    Note:
        If you pass a ``kwarg`` that starts with an **_**,
        the parameter class will store it as a regular property without the leading **_**, but it will not serialize this variable.
        This allows you to store all parameters in this object, regardless of whether you want to serialize it.

        This also works when assigning new values after the object creation:

        >>> param = ln.engine.HyperParameters()
        >>> param._dummy = 666
        >>> print(param.dummy)
        666
    """
    __init_done = False

    def __init__(self, **kwargs):
        self.batch = 0
        self.epoch = 0

        self.__no_serialize = []
        for key in kwargs:
            if key.startswith('_'):
                serialize = False
                val = kwargs[key]
                key = key[1:]
            else:
                serialize = True
                val = kwargs[key]

            if not hasattr(self, key):
                setattr(self, key, val)
                if not serialize:
                    self.__no_serialize.append(key)
            else:
                log.error(f'{key} attribute already exists as a HyperParameter and will not be overwritten.')

        self.__init_done = True

    def __setattr__(self, item, value):
        """ Store extra variables in this container class.
        This custom function allows to store objects after creation and mark whether are not you want to serialize them,
        by prefixing them with an underscore.
        """
        if item in self.__dict__ or not self.__init_done:
            super().__setattr__(item, value)
        elif item[0] == '_':
            if item[1:] in self.__dict__:
                raise AttributeError(f'{item} already stored in this object! Use {item[1:]} to access and modify it.')
            self.__no_serialize.append(item[1:])
            super().__setattr__(item[1:], value)
        else:
            super().__setattr__(item, value)

    def __repr__(self):
        """ Print all values stored in the object.
        Objects that will not be serialized are marked with an asterisk.
        """
        s = f'{self.__class__.__name__}('
        for k in sorted(self.__dict__.keys()):
            if k.startswith('_HyperParameters__'):
                continue

            val = self.__dict__[k]
            valrepr = str(val)
            if '\n' in valrepr:
                valrepr = val.__class__.__name__
            if k in self.__no_serialize:
                k += '*'

            s += f'\n  {k} = {valrepr}'

        return s + '\n)'

    @classmethod
    def from_file(cls, path, variable='params', **kwargs):
        """ Create a HyperParameter object from a dictionary in an external configuration file.
        This function will import a file by its path and extract a variable to use as HyperParameters.

        Args:
            path (str or path-like object): Path to the configuration python file
            variable (str, optional): Variable to extract from the configuration file; Default **'params'**
            **kwargs (dict, optional): Extra parameters that are passed to the extracted variable if it is a callable object

        Note:
            The extracted variable can be one of the following:

            - :class:`lightnet.engine.HyperParameters`: This object will simply be returned
            - ``dictionary``: The dictionary will be expanded as the parameters for initializing a new :class:`~lightnet.engine.HyperParameters` object
            - ``callable``: The object will be called with the optional kwargs and should return either a :class:`~lightnet.engine.HyperParameters` object or a ``dictionary``
        """
        try:
            spec = importlib.util.spec_from_file_location('lightnet.cfg', path)
            cfg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cfg)
        except AttributeError as err:
            raise ImportError(f'Failed to import the file [{path}]. Are you sure it is a valid python file?') from err

        try:
            params = getattr(cfg, variable)
        except AttributeError as err:
            raise AttributeError(f'Configuration variable [{variable}] not found in file [{path}]') from err

        if callable(params):
            params = params(**kwargs)

        if isinstance(params, cls):
            return params
        elif isinstance(params, dict):
            return cls(**params)
        else:
            raise TypeError(f'Unkown type for configuration variable {variable} [{type(params).__name__}]. This variable should be a dictionary or lightnet.engine.HyperParameters object.')

    def save(self, filename):
        """ Serialize all the hyperparameters to a pickle file. |br|
        The network, optimizers and schedulers objects are serialized using their ``state_dict()`` functions.

        Args:
            filename (str or path): File to store the hyperparameters

        Note:
            This function will first check if the existing attributes have a `state_dict()` function,
            in which case it will use this function to get the values needed to save.
        """
        state = {}

        for k, v in vars(self).items():
            if k not in self.__no_serialize:
                if hasattr(v, 'state_dict'):
                    state[k] = v.state_dict()
                else:
                    state[k] = v

        torch.save(state, filename)

    def load(self, filename, strict=True):
        """ Load the hyperparameters from a serialized pickle file.

        Note:
            This function will first check if the existing attributes have a `load_state_dict()` function,
            in which case it will use this function with the saved state to restore the values. |br|
            The `load_state_dict()` function will first be called with both the serialized value and the `strict` argument as a keyword argument.
            If that fails because of a TypeError, it is called with only the serialized value.
            This means that you will still get an error if the strict rule is not being followed,
            but functions that have a `load_state_dict()` function without `strict` argument can be loaded as well.
        """
        log.info(f'Loading state from file [{filename}]')
        state = torch.load(filename, 'cpu')

        for k, v in state.items():
            if hasattr(self, k):
                current = getattr(self, k)
                if hasattr(current, 'load_state_dict'):
                    try:
                        current.load_state_dict(v, strict=strict)
                    except TypeError:
                        current.load_state_dict(v)
                else:
                    setattr(self, k, v)
            else:
                setattr(self, k, v)

    def to(self, device):
        """ Cast the parameters from the network, optimizers and schedulers to a given device. |br|
        This function will go through all the class attributes and check if they have a `to()` function, which it will call with the device.

        Args:
            device (torch.device or string): Device to cast parameters

        Note:
            PyTorch optimizers and the ReduceLROnPlateau classes do not have a `to()` function implemented. |br|
            For these objects, this function will go through all their necessary attributes and cast the tensors to the right device.
        """
        for key, value in self.__dict__.items():
            if hasattr(value, 'to') and callable(value.to):
                value.to(device)
            elif isinstance(value, torch.optim.Optimizer):
                for param in value.state.values():
                    if isinstance(param, torch.Tensor):
                        param.data = param.data.to(device)
                        if param._grad is not None:
                            param._grad.data = param._grad.data.to(device)
                    elif isinstance(param, dict):
                        for subparam in param.values():
                            if isinstance(subparam, torch.Tensor):
                                subparam.data = subparam.data.to(device)
                                if subparam._grad is not None:
                                    subparam._grad.data = subparam._grad.data.to(device)
            elif isinstance(value, (torch.optim.lr_scheduler._LRScheduler, torch.optim.lr_scheduler.ReduceLROnPlateau)):
                for param in value.__dict__.values():
                    if isinstance(param, torch.Tensor):
                        param.data = param.data.to(device)
                        if param._grad is not None:
                            param._grad.data = param._grad.data.to(device)
