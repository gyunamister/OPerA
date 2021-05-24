from enum import Enum

from dtwin.available.available import AvailableCorrelations
from dtwin.available.ext import DtwinExtension, DtwinExtensible
from dtwin.parsedata.correlate import correlate_shared_objs, correlate_obj_path


class AvailableCorrelationsExt(Enum):
    MAXIMUM_CORRELATION = {AvailableCorrelations.MAXIMUM_CORRELATION.value:
                           DtwinExtension(name='shared object id relation (maximum)',
                                          param={
                                              'version': AvailableCorrelations.MAXIMUM_CORRELATION},
                                          typ=DtwinExtensible.CORR,
                                          call=correlate_shared_objs)
                           }
    INITIAL_PAIR_CORRELATION = {AvailableCorrelations.INITIAL_PAIR_CORRELATION.value:
                                DtwinExtension(name='shared object id relation (minimum)',
                                               param={
                                                   'version': AvailableCorrelations.INITIAL_PAIR_CORRELATION},
                                               typ=DtwinExtensible.CORR,
                                               call=correlate_shared_objs)}
    OBJ_PATH_CORRELATION = {AvailableCorrelations.OBJ_PATH_CORRELATION.value:
                            DtwinExtension(name='object path correlation',
                                           param={},
                                           typ=DtwinExtensible.CORR,
                                           call=correlate_obj_path)}


def get_available_from_name(method, default, available):
    if 'Ext' in str(default.__class__):
        return AVAILABLE_TO_EXT_AVAILABLE[method]
    else:
        return EXT_AVAILABLE_TO_AVAILABLE[method]


def extract_title(detector):
    return list(detector.value.keys())[0]


def get_available_from_name_compile_time(method, default, available):
    for candidate in available:
        if method in candidate.value:
            return candidate
    return default


EXT_AVAILABLE_TO_AVAILABLE = {
    **{extract_title(ext): get_available_from_name_compile_time(extract_title(ext),
                                                                AvailableCorrelations.MAXIMUM_CORRELATION,
                                                                AvailableCorrelations)
       for ext in AvailableCorrelationsExt}
}

AVAILABLE_TO_EXT_AVAILABLE = {
    **{ext.value: get_available_from_name_compile_time(ext.value, AvailableCorrelationsExt.OBJ_PATH_CORRELATION,
                                                       AvailableCorrelationsExt)
       for ext in AvailableCorrelations}
}
