# -*- coding: future_annotations -*-
# Copyright (c) 2018-     Xilinx, Inc              (Alessandro Pappalardo)
# Copyright (c) 2016-     Facebook, Inc            (Adam Paszke)
# Copyright (c) 2014-     Facebook, Inc            (Soumith Chintala)
# Copyright (c) 2011-2014 Idiap Research Institute (Ronan Collobert)
# Copyright (c) 2012-2014 Deepmind Technologies    (Koray Kavukcuoglu)
# Copyright (c) 2011-2012 NEC Laboratories America (Koray Kavukcuoglu)
# Copyright (c) 2011-2013 NYU                      (Clement Farabet)
# Copyright (c) 2006-2010 NEC Laboratories America (Ronan Collobert, Leon Bottou, Iain Melvin, Jason Weston)
# Copyright (c) 2006      Idiap Research Institute (Samy Bengio)
# Copyright (c) 2001-2004 Idiap Research Institute (Ronan Collobert, Samy Bengio, Johnny Mariethoz)

# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# 3. Neither the names of Xilinx, Facebook, Deepmind Technologies, NYU,
#    NEC Laboratories America and IDIAP Research Institute nor the names
#    of its contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from abc import ABC, abstractmethod
from typing import Callable, Union, Optional, TYPE_CHECKING
import math

import torch
from torch import Tensor
from torch.nn import Module

import brevitas
from brevitas.inject.enum import RestrictValueType, FloatToIntImplType  # noqa for retrocomp

from brevitas.core.function_wrapper import Identity, PowerOfTwo, LogTwo, InplaceLogTwo
from brevitas.core.function_wrapper import ScalarClampMinSte, RoundSte


class RestrictValueInterface(Module, ABC):

    @abstractmethod
    def restrict_init_float(self, x: float) -> float:
        pass

    @abstractmethod
    def restrict_init_tensor(self, x: Tensor) -> Tensor:
        pass

    @abstractmethod
    def restrict_init_module(self) -> Module:
        pass

    @abstractmethod
    def restrict_init_inplace_module(self) -> Module:
        pass


if TYPE_CHECKING or brevitas.config.JIT_ENABLED:
    RestrictValue = RestrictValueInterface
else:
    RestrictValue = brevitas.jit.ScriptModule


class _RestrictClampValue(brevitas.jit.ScriptModule):

    def __init__(
            self,
            scaling_min_val: Optional[float],
            restrict_value_impl: Optional[Module]):
        super(_RestrictClampValue, self).__init__()
        if scaling_min_val is not None and scaling_min_val != 0:
            if restrict_value_impl is not None:
                scaling_min_val = restrict_value_impl.restrict_init_float(scaling_min_val)
            self.clamp_min_ste = ScalarClampMinSte(scaling_min_val)
        else:
            self.clamp_min_ste = Identity()
        if restrict_value_impl is not None:
            self.restrict_value_impl = restrict_value_impl
        else:
            self.restrict_value_impl = Identity()

    @brevitas.jit.script_method
    def forward(self, x: torch.Tensor):
        x = self.clamp_min_ste(x)
        return self.restrict_value_impl(x)


class FloatRestrictValue(RestrictValueInterface):

    def __init__(self) -> None:
        super(FloatRestrictValue, self).__init__()

    def restrict_init_float(self, x: float) -> float:
        return x

    def restrict_init_tensor(self, x: Tensor) -> Tensor:
        return x

    def restrict_init_module(self):
        return Identity()

    def restrict_init_inplace_module(self):
        return Identity()

    @brevitas.jit.script_method
    def forward(self, x: torch.Tensor) -> Tensor:
        return x


class LogFloatRestrictValue(RestrictValueInterface):

    def __init__(self):
        super(LogFloatRestrictValue, self).__init__()
        self.power_of_two: Module = PowerOfTwo()

    def restrict_init_float(self, x: float):
        return math.log2(x)

    def restrict_init_tensor(self, x: torch.Tensor):
        return torch.log2(x)

    def restrict_init_module(self):
        return LogTwo()

    def restrict_init_inplace_module(self):
        return InplaceLogTwo()

    @brevitas.jit.script_method
    def forward(self, x: torch.Tensor):
        x = self.power_of_two(x)
        return x


class IntRestrictValue(RestrictValueInterface):

    def __init__(self, restrict_value_float_to_int_impl: Module = RoundSte()):
        super(IntRestrictValue, self).__init__()
        self.float_to_int_impl = restrict_value_float_to_int_impl

    def restrict_init_float(self, x: float):
        return x

    def restrict_init_tensor(self, x: torch.Tensor):
        return x

    def restrict_init_module(self):
        return Identity()

    def restrict_init_inplace_module(self):
        return Identity()

    @brevitas.jit.script_method
    def forward(self, x: torch.Tensor):
        x = self.float_to_int_impl(x)
        return x


class PowerOfTwoRestrictValue(RestrictValueInterface):

    def __init__(self, restrict_value_float_to_int_impl: Module = RoundSte()):
        super(PowerOfTwoRestrictValue, self).__init__()
        self.float_to_int_impl = restrict_value_float_to_int_impl
        self.power_of_two: Module = PowerOfTwo()

    def restrict_init_float(self, x: float):
        return math.log2(x)

    def restrict_init_tensor(self, x: torch.Tensor):
        return torch.log2(x)

    def restrict_init_module(self):
        return LogTwo()

    def restrict_init_inplace_module(self):
        return InplaceLogTwo()

    @brevitas.jit.script_method
    def forward(self, x: torch.Tensor):
        x = self.float_to_int_impl(x)
        x = self.power_of_two(x)
        return x
