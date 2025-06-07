import json
import os
import CoreAudio
import ctypes
import time
import sounddevice as sd

class AudioObjectPropertyAddress(ctypes.Structure):
    _fields_ = [
        ('mSelector', ctypes.c_uint32),
        ('mScope', ctypes.c_uint32),
        ('mElement', ctypes.c_uint32)
    ]

core_audio = ctypes.CDLL('/System/Library/Frameworks/CoreAudio.framework/CoreAudio')
core_audio.AudioObjectGetPropertyData.argtypes = [
    ctypes.c_uint32,
    ctypes.POINTER(AudioObjectPropertyAddress),
    ctypes.c_uint32,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.c_void_p
]
core_audio.AudioObjectGetPropertyData.restype = ctypes.c_int32


class AudioStreamBasicDescription(ctypes.Structure):
    _fields_ = [
        ('mSampleRate', ctypes.c_double),
        ('mFormatID', ctypes.c_uint32),
        ('mFormatFlags', ctypes.c_uint32),
        ('mBytesPerPacket', ctypes.c_uint32),
        ('mFramesPerPacket', ctypes.c_uint32),
        ('mBytesPerFrame', ctypes.c_uint32),
        ('mChannelsPerFrame', ctypes.c_uint32),
        ('mBitsPerChannel', ctypes.c_uint32),
        ('mReserved', ctypes.c_uint32)
    ]


def stream_default_output_device_info():
    while True:
        info = {
            "name": None,
            "sample_rate": None
        }

        address = AudioObjectPropertyAddress(
            mSelector=CoreAudio.kAudioHardwarePropertyDefaultOutputDevice,
            mScope=CoreAudio.kAudioObjectPropertyScopeGlobal,
            mElement=CoreAudio.kAudioObjectPropertyElementMaster
        )
        device_id = ctypes.c_uint32()
        size = ctypes.c_uint32(ctypes.sizeof(ctypes.c_uint32))
        core_audio.AudioObjectGetPropertyData(
            CoreAudio.kAudioObjectSystemObject,
            ctypes.byref(address),
            0,
            None,
            ctypes.byref(size),
            ctypes.byref(device_id)
        )
        device_id_value = device_id.value

        try:
            device = sd.query_devices(kind='output')
            info["name"] = device["name"]
        except Exception:
            info["name"] = None

        stream_address = AudioObjectPropertyAddress(
            mSelector=CoreAudio.kAudioDevicePropertyStreamFormat,
            mScope=CoreAudio.kAudioDevicePropertyScopeOutput,
            mElement=0
        )

        fmt = AudioStreamBasicDescription()
        size = ctypes.c_uint32(ctypes.sizeof(fmt))
        core_audio.AudioObjectGetPropertyData(
            device_id_value,
            stream_address,
            0,
            None,
            ctypes.byref(size),
            ctypes.byref(fmt)
        )

        info["bit_depth"] = fmt.mBitsPerChannel
        info["sample_rate"] = int(fmt.mSampleRate)
        with open("device.json", "w") as f:
            json.dump(info, f, indent=2)

        time.sleep(1)


if __name__ == "__main__":
    stream_default_output_device_info()