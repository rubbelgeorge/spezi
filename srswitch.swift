#!/usr/bin/env swift

import Foundation
import CoreAudio

// MARK: - Parse Command-Line Argument
guard CommandLine.arguments.count > 1,
      let argRate = Double(CommandLine.arguments[1]) else {
    print("Usage: ./test.swift <sampleRate>   (e.g. 44100, 96000)")
    exit(1)
}

let desiredSampleRate: Float64 = argRate

// MARK: - Helpers

func getDefaultOutputDeviceID() -> AudioDeviceID? {
    var defaultDeviceID = AudioDeviceID(0)
    var size = UInt32(MemoryLayout<AudioDeviceID>.size)

    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )

    let status = AudioObjectGetPropertyData(
        AudioObjectID(kAudioObjectSystemObject),
        &address,
        0,
        nil,
        &size,
        &defaultDeviceID
    )

    return status == noErr ? defaultDeviceID : nil
}

func setSampleRate(deviceID: AudioDeviceID, sampleRate: Float64) -> Bool {
    var rate = sampleRate
    let size = UInt32(MemoryLayout<Float64>.size)

    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyNominalSampleRate,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )

    let status = AudioObjectSetPropertyData(
        deviceID,
        &address,
        0,
        nil,
        size,
        &rate
    )

    return status == noErr
}

func getCurrentSampleRate(deviceID: AudioDeviceID) -> Float64? {
    var rate = Float64(0)
    var size = UInt32(MemoryLayout<Float64>.size)

    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyNominalSampleRate,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )

    let status = AudioObjectGetPropertyData(
        deviceID,
        &address,
        0,
        nil,
        &size,
        &rate
    )

    return status == noErr ? rate : nil
}

// MARK: - Execution

if let deviceID = getDefaultOutputDeviceID() {
    let success = setSampleRate(deviceID: deviceID, sampleRate: desiredSampleRate)
    if success {
        print("✅ Set sample rate to \(Int(desiredSampleRate)) Hz")
    } else {
        print("❌ Failed to set sample rate")
    }
} else {
    print("❌ Could not get default output device ID")
}