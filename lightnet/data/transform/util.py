#
#   Lightnet related data processing
#   Utilitary classes and functions for the data subpackage
#   Copyright EAVISE
#

import logging
from abc import ABC, abstractmethod
from PIL import Image
import numpy as np

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

__all__ = ['Compose']
log = logging.getLogger(__name__)


class Compose(list):
    """ This is lightnet's own version of :class:`torchvision.transforms.Compose`.

    Note:
        The reason we have our own version is because this one offers more freedom to the user.
        For all intends and purposes this class is just a list.
        This `Compose` version allows the user to access elements through index, append items, extend it with another list, etc.
        When calling instances of this class, it behaves just like :class:`torchvision.transforms.Compose`.

    Note:
        I proposed to change :class:`torchvision.transforms.Compose` to something similar to this version,
        which would render this class useless. In the meanwhile, we use our own version
        and you can track `the issue`_ to see if and when this comes to torchvision.

    Example:
        >>> tf = ln.data.transform.Compose([lambda n: n+1])
        >>> tf(10)  # 10+1
        11
        >>> tf.append(lambda n: n*2)
        >>> tf(10)  # (10+1)*2
        22
        >>> tf.insert(0, lambda n: n//2)
        >>> tf(10)  # ((10//2)+1)*2
        12
        >>> del tf[2]
        >>> tf(10)  # (10//2)+1
        6

    .. _the issue: https://github.com/pytorch/vision/issues/456
    """
    def __call__(self, data):
        for tf in self:
            data = tf(data)
        return data

    def __repr__(self):
        format_string = self.__class__.__name__ + ' ['
        for tf in self:
            if hasattr(tf, '__name__'):
                name = tf.__name__
            else:
                name = tf.__class__.__name__

            format_string += f'\n  {name}'
        format_string += '\n]'
        return format_string


class BaseTransform(ABC):
    """ Base transform class for the pre- and post-processing functions.
    This class allows to create an object with some case specific settings, and then call it with the data to perform the transformation.
    It also allows to call the static method ``apply`` with the data and settings. This is usefull if you want to transform a single data object.
    """
    @abstractmethod
    def __call__(self, data):
        return data

    @classmethod
    def apply(cls, data, **kwargs):
        """ Classmethod that applies the transformation once.

        Args:
            data: Data to transform (eg. image)
            **kwargs: Same arguments that are passed to the ``__init__`` function
        """
        obj = cls(**kwargs)
        return obj(data)


class BaseMultiTransform(ABC):
    """ Base multiple transform class that is mainly used in pre-processing functions.
    This class exists for transforms that affect both images and annotations.
    It provides a classmethod ``apply``, that will perform the transormation on one (data, target) pair.
    """
    def __call__(self, data):
        if data is None:
            return None
        elif pd is not None and isinstance(data, pd.DataFrame):
            return self._tf_anno(data)
        elif isinstance(data, Image.Image):
            return self._tf_pil(data)
        elif isinstance(data, np.ndarray):
            return self._tf_cv(data)
        else:
            log.error(f'{self.__class__.__name__} only works with <brambox annotation dataframes>, <PIL images> or <OpenCV images> [{type(data)}]')
            return data

    @classmethod
    def apply(cls, data, target=None, **kwargs):
        """ Classmethod that applies the transformation once.

        Args:
            data: Data to transform (eg. image)
            target (optional): ground truth for that data; Default **None**
            **kwargs: Same arguments that are passed to the ``__init__`` function
        """
        obj = cls(**kwargs)
        res_data = obj(data)

        if target is None:
            return res_data

        res_target = obj(target)
        return res_data, res_target

    @abstractmethod
    def _tf_pil(self, img):
        return img

    @abstractmethod
    def _tf_cv(self, img):
        return img

    @abstractmethod
    def _tf_anno(self, anno):
        return anno
